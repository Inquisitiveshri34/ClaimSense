"""Fixture manifest (NFR-02, NFR-09, R2, R5; test-fixtures.md §1, §9): listed, hashed, small."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from typing import Any

import pytest
import yaml

from claimsense import config
from claimsense.collect.sources import FIXTURE_POLICY_SAVED_ALLOWED, load_registry
from claimsense.schema import SOURCES

REPO = config.repo_root()
FIXTURES = REPO / "tests" / "fixtures"
MANIFEST = FIXTURES / "FIXTURES.yaml"
MAKE_PDFS = FIXTURES / "_build" / "make_pdfs.py"

KINDS = ("synthetic", "saved-redacted", "saved")
# Size limits from test-fixtures.md §1 rule 3.
MAX_PDF_BYTES = 200 * 1024
MAX_HTML_BYTES = 300 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024


def _entries() -> list[dict[str, Any]]:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or []


def _is_fixture(path: Path) -> bool:
    """Whether a file under tests/fixtures/ is a fixture (not the manifest or build code)."""
    if path == MANIFEST or path.name == ".gitkeep" or "__pycache__" in path.parts:
        return False
    return not (path.suffix == ".py" and FIXTURES / "_build" in path.parents)


def _fixture_files() -> list[Path]:
    return sorted(p for p in FIXTURES.rglob("*") if p.is_file() and _is_fixture(p))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_every_fixture_file_is_listed_once() -> None:
    listed = [entry["path"] for entry in _entries()]
    on_disk = [path.relative_to(FIXTURES).as_posix() for path in _fixture_files()]

    assert sorted(listed) == sorted(set(listed)), "an entry is listed twice"
    assert sorted(listed) == on_disk


@pytest.mark.parametrize("entry", _entries(), ids=lambda entry: entry["path"])
def test_entry_is_complete_and_matches_the_file(entry: dict[str, Any]) -> None:
    path = FIXTURES / entry["path"]

    assert path.is_file()
    assert entry["sha256"] == _sha256(path), "fixture changed: add a new file (_v2) or fix the hash"
    assert entry["kind"] in KINDS
    assert entry["contains_personal_data"] is False
    assert entry["used_by"], "a fixture nobody uses should be removed"
    for user in entry["used_by"]:
        assert (REPO / user).is_file(), f"used_by path does not exist: {user}"
    if entry["kind"] != "synthetic":
        assert entry.get("captured"), "a saved fixture records its capture date"
    if entry["kind"] == "saved-redacted":
        assert entry.get("redaction_reviewed_by"), "a redacted page needs a human reviewer"


@pytest.mark.parametrize("entry", _entries(), ids=lambda entry: entry["path"])
def test_unredacted_pages_only_from_cleared_sources(entry: dict[str, Any], clean_env: None) -> None:
    source = entry.get("source")
    if source is None:
        return
    assert source in SOURCES
    if entry["kind"] == "saved":
        policy = load_registry(config.load()).fixture_policy(source)
        assert policy == FIXTURE_POLICY_SAVED_ALLOWED, f"{source} fixtures must be {policy}"


def test_fixtures_are_small() -> None:
    files = _fixture_files()
    for path in files:
        size = path.stat().st_size
        if path.suffix == ".pdf":
            assert size <= MAX_PDF_BYTES, path
        if path.suffix in (".html", ".htm"):
            assert size <= MAX_HTML_BYTES, path
    assert sum(path.stat().st_size for path in files) <= MAX_TOTAL_BYTES


def test_synthetic_pdfs_rebuild_byte_identically(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("make_pdfs", MAKE_PDFS)
    assert spec is not None and spec.loader is not None
    make_pdfs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(make_pdfs)

    built = make_pdfs.build_all(tmp_path)

    assert built
    for path in built:
        committed = FIXTURES / path.relative_to(tmp_path)
        assert _sha256(path) == _sha256(committed), path.name
    # Building twice gives the same bytes again.
    again = make_pdfs.build_all(tmp_path / "again")
    assert [_sha256(p) for p in again] == [_sha256(p) for p in built]
