"""verify and report (FR-02b, FR-03; runbook §5, §8): the store matches the manifest."""

from __future__ import annotations

import io

import pytest

from claimsense import paths
from claimsense.collect.__main__ import main
from claimsense.collect.cioins import CioinsCollector
from claimsense.collect.manifest import (
    PARTIAL_DIRNAME,
    Manifest,
    Problem,
    manifest_path,
    raw_root,
)
from claimsense.config import Config
from tests.collect.helpers import FIXTURES, flip_first_byte, run_collector
from tests.stubs.fake_clock import FakeClock
from tests.stubs.fake_http import FakeTransport

URLMAP = FIXTURES / "cioins" / "urlmap.yaml"


@pytest.fixture
def stored(cioins_cfg: Config) -> Config:
    """A config whose store holds one completed CIOINS run."""
    stats, _ = run_collector(CioinsCollector, cioins_cfg, URLMAP)
    assert stats.stored == 2
    return cioins_cfg


def _problems(cfg: Config) -> list[Problem]:
    with Manifest(manifest_path(cfg)) as manifest:
        return manifest.verify(raw_root(cfg))


def _first_file(cfg: Config):
    with Manifest(manifest_path(cfg)) as manifest:
        row = manifest.rows()[0]
    return row, raw_root(cfg) / row.file_path


def _cli(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    return main(list(argv), out=out), out.getvalue()


def test_clean_store_has_no_problems(stored: Config) -> None:
    assert _problems(stored) == []
    code, output = _cli("verify")
    assert code == 0
    assert "2 rows checked · 0 problems" in output


def test_deleted_file_is_missing(stored: Config) -> None:
    row, path = _first_file(stored)
    path.unlink()

    assert _problems(stored) == [Problem("missing", row.file_path, row.doc_id)]
    code, output = _cli("verify")
    assert code != 0
    assert f"missing: {row.file_path}" in output


def test_changed_byte_is_a_hash_mismatch(stored: Config) -> None:
    row, path = _first_file(stored)
    flip_first_byte(path)

    assert _problems(stored) == [Problem("hash_mismatch", row.file_path, row.doc_id)]
    code, output = _cli("verify")
    assert code != 0
    assert "hash_mismatch" in output and row.doc_id in output


def test_file_without_a_row_and_leftover_partial_are_reported(stored: Config) -> None:
    raw = paths.raw_dir("cioins", stored)
    (raw / "stray.pdf").write_bytes(b"not in the manifest")
    (raw / PARTIAL_DIRNAME).mkdir(exist_ok=True)
    (raw / PARTIAL_DIRNAME / "half.pdf").write_bytes(b"half a download")

    assert sorted(p.kind for p in _problems(stored)) == ["orphan_file", "partial"]
    assert _cli("verify")[0] != 0


def test_report_counts_by_status_year_and_office(stored: Config) -> None:
    code, output = _cli("report")

    assert code == 0
    by_status, by_year, by_office = output.split("by ")[1:]
    assert by_status.split() == [
        "status:", "duplicate", "1", "failed", "1", "filtered", "1", "stored", "2",
    ]  # fmt: skip
    assert by_year.split() == ["year:", "2023", "2"]
    assert by_office.split() == ["office:", "Ahmedabad", "1", "Bhopal", "1"]


def test_run_command_prints_the_summary_line(cioins_cfg: Config) -> None:
    clock = FakeClock()
    out = io.StringIO()

    code = main(
        ["run", "--source", "cioins"],
        transport=FakeTransport.from_urlmap(URLMAP, clock),
        clock=clock,
        out=out,
    )

    assert code == 0
    assert out.getvalue().startswith(
        "cioins: listed 5 · stored 2 · filtered 1 · duplicate 1 · failed 1 · "
        "skipped(already have) 0"
    )
    assert _problems(cioins_cfg) == []


def test_run_command_fails_cleanly_for_a_disabled_source(
    cioins_cfg: Config, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from claimsense import config

    monkeypatch.delenv(config.OVERRIDE_ENV_VAR)  # back to the repo config: CIOINS disabled
    clock = FakeClock()

    code = main(
        ["run", "--source", "cioins", "--dry-run"],
        transport=FakeTransport.from_urlmap(URLMAP, clock),
        clock=clock,
        out=io.StringIO(),
    )

    assert code == 1
    assert "enabled: false" in capsys.readouterr().err
