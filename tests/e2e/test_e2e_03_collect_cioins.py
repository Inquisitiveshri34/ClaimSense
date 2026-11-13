"""E2E stage 03 (FR-01, FR-02, FR-03, NFR-08): the CIOINS collector on the synthetic world."""

from __future__ import annotations

import io
from datetime import date

import pytest

from claimsense import config, paths
from claimsense.collect.__main__ import main as collect_main
from claimsense.collect.manifest import (
    STATUS_FILTERED,
    STATUS_STORED,
    Manifest,
    manifest_path,
    raw_root,
    sha256_file,
)
from claimsense.schema import LABELS
from tests.e2e import stages
from tests.e2e.conftest import E2EWorld
from tests.e2e.corpus import DECISIONS_PER_SOURCE

pytestmark = pytest.mark.e2e

SOURCE = "cioins"


def test_collect_stores_every_health_award(world: E2EWorld) -> None:
    corpus = stages.run_corpus(world)
    result = stages.run_collect(world)
    run = result.runs[SOURCE]
    health = corpus.health(SOURCE)
    distractors = corpus.distractors(SOURCE)

    # (a) the stage runs: 30 stored, every non-health award filtered, nothing failed.
    assert run.exit_code == 0, run.output
    assert len(health) == DECISIONS_PER_SOURCE
    assert run.count("stored") == DECISIONS_PER_SOURCE
    assert run.count("filtered") == len(distractors) > 0
    assert run.count("failed") == 0 and run.count("duplicate") == 0
    assert not {d.url for d in distractors} & set(run.requested_urls), "a distractor was fetched"

    # (b) manifest rows match the corpus ground truth.
    rows = {row.doc_id: row for row in result.rows}
    assert set(rows) == {d.doc_id for d in health}
    for decision in health:
        row = rows[decision.doc_id]
        assert row.source == SOURCE
        assert date.fromisoformat(row.decision_date) == decision.decision_date
        assert (row.office, row.insurer, row.product) == (
            decision.office,
            decision.insurer,
            decision.product,
        )
        assert row.url == decision.url

    with Manifest(manifest_path(world.cfg)) as manifest:
        assert manifest.gaps() == []
        statuses = {entry.url: entry.status for entry in manifest.crawl_entries()}
    assert all(statuses[d.url] == STATUS_FILTERED for d in distractors)
    assert all(statuses[d.url] == STATUS_STORED for d in health)

    out = io.StringIO()
    assert collect_main(["verify"], out=out) == 0, out.getvalue()
    assert f"{DECISIONS_PER_SOURCE} rows checked · 0 problems" in out.getvalue()


def test_collecting_again_stores_nothing(world: E2EWorld) -> None:
    first = stages.run_collect(world)

    again = stages.collect_once(world, SOURCE)

    assert again.exit_code == 0, again.output
    assert again.count("stored") == 0
    assert again.count("skipped(already have)") == first.runs[SOURCE].count("listed")
    assert not [url for url in again.requested_urls if url.endswith(".pdf")]
    with Manifest(manifest_path(world.cfg)) as manifest:
        assert tuple(manifest.rows()) == first.rows


def test_stored_files_are_hashed_and_stay_inside_the_world(world: E2EWorld) -> None:
    result = stages.run_collect(world)
    raw_dir = paths.raw_dir(SOURCE)

    assert raw_dir.is_relative_to(world.root)
    stored = sorted(raw_dir.glob("*.pdf"))
    assert len(stored) == len(result.rows) == DECISIONS_PER_SOURCE
    hashes = {row.file_sha256 for row in result.rows}
    assert len(hashes) == len(result.rows)
    for path in stored:
        assert sha256_file(path) in hashes
    for row in result.rows:
        assert (raw_root(world.cfg) / row.file_path).is_file()

    # Nothing was written to the repo's own data folder.
    repo_data = config.repo_root() / "data"
    assert sorted(p.name for p in repo_data.iterdir()) == [".gitkeep", "README.md"]


def test_corpus_gives_later_stages_what_they_need(world: E2EWorld) -> None:
    corpus = stages.run_corpus(world)
    health = corpus.health(SOURCE)

    # Labels are balanced and every split of the temporal split gets data.
    assert {label: sum(d.label == label for d in health) for label in LABELS} == {
        label: DECISIONS_PER_SOURCE // len(LABELS) for label in LABELS
    }
    years = {d.decision_date.year for d in health}
    assert min(years) == 2019 and max(years) == 2025 and {2023, 2024, 2025} <= years

    # A weak signal in the facts: the cue agrees with the label more often than not, not always.
    agree = sum(d.cue_label == d.label for d in health)
    assert len(health) / 2 < agree < len(health)

    # Every decision has all four sections and carries fictional personal data to scrub.
    for decision in health:
        assert all(
            decision.sections[key] for key in ("complaint", "insurer_position", "findings", "award")
        )
        assert decision.pii["name"] in decision.text
        assert decision.pii["policy_number"] in decision.text
    assert len({d.pii["name"] for d in health}) == len(health)

    # The same seed gives the same world.
    again = stages.build_corpus(world.root / "sites-again", corpus.seed, world.cfg)
    assert again.decisions == corpus.decisions
