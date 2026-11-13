"""Manifest schema (FR-02a; data-schema.md §2): columns, types, constraints, uniqueness."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from claimsense.collect.manifest import (
    STATUS_FAILED,
    STATUSES,
    CrawlEntry,
    Manifest,
    ManifestRow,
)
from claimsense.schema import SOURCES

# data-schema.md §2: column -> (declared type, NOT NULL)
MANIFEST_COLUMNS = {
    "doc_id": ("TEXT", False),  # primary key
    "source": ("TEXT", True),
    "url": ("TEXT", True),
    "decision_date": ("TEXT", True),
    "insurer": ("TEXT", True),
    "product": ("TEXT", True),
    "outcome_raw": ("TEXT", True),
    "office": ("TEXT", False),
    "file_path": ("TEXT", True),
    "file_sha256": ("TEXT", True),
    "mime_type": ("TEXT", True),
    "fetched_at": ("TEXT", True),
    "collector_version": ("TEXT", True),
}
CRAWL_COLUMNS = {
    "url": ("TEXT", False),  # primary key
    "source": ("TEXT", True),
    "status": ("TEXT", True),
    "reason": ("TEXT", False),
    "seen_at": ("TEXT", True),
}


def _row(n: int = 1, **changes: object) -> ManifestRow:
    row = ManifestRow(
        doc_id=f"cioins-2023-05-1004-{n:04d}",
        source="cioins",
        url=f"test://site/award-{n}.pdf",
        decision_date="2023-05-12",
        insurer="Fictional General Insurance Co. Ltd.",
        product="individual_mediclaim",
        outcome_raw="",
        office="Demo Office",
        file_path=f"cioins/cioins-2023-05-1004-{n:04d}.pdf",
        file_sha256=f"{n:064x}",
        mime_type="application/pdf",
        fetched_at="2026-01-01T00:00:00Z",
        collector_version="1.0.0",
    )
    return replace(row, **changes)


@pytest.fixture
def manifest(tmp_path: Path) -> Manifest:
    return Manifest(tmp_path / "manifests" / "manifest.sqlite")


def _columns(manifest: Manifest, table: str) -> dict[str, tuple[str, bool]]:
    with sqlite3.connect(manifest.path) as db:
        info = db.execute(f"PRAGMA table_info({table})").fetchall()
    return {name: (kind, bool(notnull)) for _, name, kind, notnull, _, _ in info}


def test_manifest_columns_and_types(manifest: Manifest) -> None:
    assert _columns(manifest, "manifest") == MANIFEST_COLUMNS
    assert _columns(manifest, "crawl_log") == CRAWL_COLUMNS


def test_row_round_trips(manifest: Manifest) -> None:
    row = _row()
    manifest.upsert(row)

    assert manifest.rows() == [row]
    assert manifest.get(row.doc_id) == row
    assert manifest.has_url(row.url)
    assert manifest.has_hash(row.file_sha256)
    assert date.fromisoformat(manifest.rows()[0].decision_date) == date(2023, 5, 12)


@pytest.mark.parametrize(
    "field",
    [name for name, (_, required) in MANIFEST_COLUMNS.items() if required],
)
def test_required_fields_cannot_be_null(manifest: Manifest, field: str) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        manifest.upsert(_row(**{field: None}))


@pytest.mark.parametrize("value", ["12-05-2023", "2023-5-12", "2023/05/12", "May 2023", ""])
def test_decision_date_must_be_iso(manifest: Manifest, value: str) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        manifest.upsert(_row(decision_date=value))


def test_source_is_constrained(manifest: Manifest) -> None:
    for n, source in enumerate(SOURCES, start=1):
        manifest.upsert(_row(n, source=source))
    with pytest.raises(sqlite3.IntegrityError):
        manifest.upsert(_row(99, source="elsewhere"))


def test_product_must_be_a_health_product(manifest: Manifest) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        manifest.upsert(_row(product="motor"))


def test_sha256_must_be_64_chars_and_unique(manifest: Manifest) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        manifest.upsert(_row(file_sha256="abc"))
    manifest.upsert(_row(1))
    with pytest.raises(sqlite3.IntegrityError):
        manifest.upsert(_row(2, file_sha256=_row(1).file_sha256))


def test_doc_id_is_unique(manifest: Manifest) -> None:
    manifest.upsert(_row(1))
    manifest.upsert(_row(1, insurer="Madeup Health Insurance Ltd."))  # same doc_id: replaced

    assert len(manifest.rows()) == 1
    assert manifest.rows()[0].insurer == "Madeup Health Insurance Ltd."
    with sqlite3.connect(manifest.path) as db, pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO manifest SELECT * FROM manifest")  # a plain second insert must fail


def test_status_is_constrained(manifest: Manifest) -> None:
    for n, status in enumerate(STATUSES):
        manifest.log(CrawlEntry(f"test://site/{n}", "cioins", status, None, "2026-01-01T00:00:00Z"))
    with pytest.raises(sqlite3.IntegrityError):
        manifest.log(CrawlEntry("test://site/x", "cioins", "lost", None, "2026-01-01T00:00:00Z"))


def test_failed_urls_are_gaps_and_are_not_settled(manifest: Manifest) -> None:
    failed = CrawlEntry("test://site/gone.pdf", "cioins", STATUS_FAILED, "HTTP 404", "2026-01-01")
    manifest.log(failed)
    manifest.upsert(_row())

    assert manifest.gaps() == [failed]
    assert not manifest.has_url(failed.url)  # retried on the next run
    assert manifest.report()["status"] == {"failed": 1, "stored": 1}


def test_reopening_keeps_the_rows(manifest: Manifest) -> None:
    manifest.upsert(_row())
    manifest.close()
    with Manifest(manifest.path) as reopened:
        assert reopened.rows() == [_row()]
