"""Resume (FR-03; runbook §5; test-fixtures.md §4): the four resume scenarios."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from claimsense import paths
from claimsense.collect.cioins import CioinsCollector
from claimsense.collect.manifest import (
    PARTIAL_DIRNAME,
    STATUS_DUPLICATE,
    Manifest,
    ManifestRow,
    manifest_path,
    raw_root,
)
from claimsense.config import Config
from tests.collect.helpers import FIXTURES, flip_first_byte, run_collector
from tests.e2e.corpus import build_corpus
from tests.stubs.fake_http import SimulatedCrash

CIOINS = FIXTURES / "cioins"
URLMAP = CIOINS / "urlmap.yaml"


def _rows(cfg: Config) -> list[ManifestRow]:
    with Manifest(manifest_path(cfg)) as manifest:
        return manifest.rows()


def test_second_run_stores_nothing(cioins_cfg: Config) -> None:
    first, _ = run_collector(CioinsCollector, cioins_cfg, URLMAP)
    rows_after_first = _rows(cioins_cfg)

    second, transport = run_collector(CioinsCollector, cioins_cfg, URLMAP)

    assert first.stored == 2
    assert second.stored == 0  # FR-03a
    assert second.skipped == first.stored + first.filtered + first.duplicate
    assert _rows(cioins_cfg) == rows_after_first
    # Only the dead link is tried again; nothing that is already held is fetched.
    (dead_link,) = (
        url for url, served in yaml.safe_load(URLMAP.read_text()).items() if served == "@404"
    )
    assert transport.urls(".pdf") == [dead_link]


def test_interrupted_run_completes_on_rerun(cioins_cfg: Config, tmp_path: Path) -> None:
    corpus = build_corpus(tmp_path / "sites", cioins_cfg.project.seed, cioins_cfg)
    urlmap = corpus.urlmaps["cioins"]
    expected = {d.doc_id for d in corpus.health("cioins")}

    with pytest.raises(SimulatedCrash):
        run_collector(CioinsCollector, cioins_cfg, urlmap, crash_after=3)
    assert len(_rows(cioins_cfg)) == 3
    # The crash can leave a half-written download behind.
    partial_dir = paths.raw_dir("cioins", cioins_cfg) / PARTIAL_DIRNAME
    partial_dir.mkdir(exist_ok=True)
    (partial_dir / "interrupted.pdf").write_bytes(b"half a download")

    rerun, _ = run_collector(CioinsCollector, cioins_cfg, urlmap)

    rows = _rows(cioins_cfg)
    assert rerun.stored == len(expected) - 3 and rerun.failed == 0
    assert {row.doc_id for row in rows} == expected  # no gaps (FR-03b)
    assert len({row.doc_id for row in rows}) == len(rows)
    assert len({row.file_sha256 for row in rows}) == len(rows)
    assert not partial_dir.exists() or not any(partial_dir.iterdir())
    with Manifest(manifest_path(cioins_cfg)) as manifest:
        assert manifest.gaps() == []
        assert manifest.verify(raw_root(cioins_cfg)) == []


def test_tampered_file_is_reported_then_downloaded_again(cioins_cfg: Config) -> None:
    run_collector(CioinsCollector, cioins_cfg, URLMAP)
    row = _rows(cioins_cfg)[0]
    path = raw_root(cioins_cfg) / row.file_path
    flip_first_byte(path)

    with Manifest(manifest_path(cioins_cfg)) as manifest:
        problems = manifest.verify(raw_root(cioins_cfg))
    assert [(p.kind, p.doc_id) for p in problems] == [("hash_mismatch", row.doc_id)]

    rerun, transport = run_collector(CioinsCollector, cioins_cfg, URLMAP)

    assert rerun.stored == 1
    assert row.url in transport.urls()
    assert _rows(cioins_cfg)[0].file_sha256 == row.file_sha256
    with Manifest(manifest_path(cioins_cfg)) as manifest:
        assert manifest.verify(raw_root(cioins_cfg)) == []


def test_same_bytes_under_two_urls_is_a_duplicate(cioins_cfg: Config) -> None:
    urlmap = yaml.safe_load(URLMAP.read_text(encoding="utf-8"))
    first_url, second_url = (url for url, served in urlmap.items() if served == "award_text.pdf")

    stats, _ = run_collector(CioinsCollector, cioins_cfg, URLMAP)

    assert stats.duplicate == 1
    rows = _rows(cioins_cfg)
    (holder,) = (row for row in rows if row.url == first_url)
    assert second_url not in {row.url for row in rows}
    with Manifest(manifest_path(cioins_cfg)) as manifest:
        (entry,) = (e for e in manifest.crawl_entries() if e.url == second_url)
    assert entry.status == STATUS_DUPLICATE
    assert holder.doc_id in (entry.reason or "")
    stored = sorted(paths.raw_dir("cioins", cioins_cfg).glob("*.pdf"))
    assert len(stored) == len(rows) == 2  # the second copy is not kept
