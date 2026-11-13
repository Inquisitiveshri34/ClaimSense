"""Repository guard (NFR-10; ci-cd.md §3.4, risks R5, R14): scripts/ci_guard.sh in a temp repo."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from claimsense import config

GUARD = config.repo_root() / "scripts" / "ci_guard.sh"
GITIGNORE = config.repo_root() / ".gitignore"

# Built from parts so that this file itself passes the no-network-in-tests rule.
URL = "https" + "://example.org"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """An empty git repository holding only the files the guard allows."""
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    # The rule gitignore-covers-data (PR 2) needs the project's ignore rules.
    shutil.copy(GITIGNORE, tmp_path / ".gitignore")
    subprocess.run(["git", "add", "--", ".gitignore"], cwd=tmp_path, check=True)
    _track(tmp_path, "data/.gitkeep")
    _track(tmp_path, "data/README.md", "local only\n")
    _track(tmp_path, ".env.example", "GROQ_API_KEY=\n")
    _track(tmp_path, "tests/test_ok.py", "def test_ok():\n    assert True\n")
    return tmp_path


def _track(repo: Path, relative: str, content: str = "") -> None:
    """Write a file and add it to the index (force past any ignore rule)."""
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "--force", "--", relative], cwd=repo, check=True)


def _run_guard(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(GUARD)], cwd=repo, capture_output=True, text=True)


def test_clean_repo_passes(repo: Path) -> None:
    result = _run_guard(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "FAIL" not in result.stdout


def test_tracked_data_file_fails(repo: Path) -> None:
    _track(repo, "data/raw/x.txt", "raw text\n")
    result = _run_guard(repo)
    assert result.returncode != 0
    assert "FAIL  no-data-tracked" in result.stdout
    assert "data/raw/x.txt" in result.stdout


@pytest.mark.parametrize("name", [".env", "kaggle.json", "certs/server.pem"])
def test_tracked_secrets_file_fails(repo: Path, name: str) -> None:
    _track(repo, name, "x\n")
    result = _run_guard(repo)
    assert result.returncode != 0
    assert "FAIL  no-secrets-files" in result.stdout


def test_pdf_outside_fixtures_fails(repo: Path) -> None:
    _track(repo, "a.pdf", "%PDF-1.4\n")
    result = _run_guard(repo)
    assert result.returncode != 0
    assert "FAIL  no-pdfs" in result.stdout


def test_pdf_in_fixtures_allowed(repo: Path) -> None:
    _track(repo, "tests/fixtures/a.pdf", "%PDF-1.4\n")
    result = _run_guard(repo)
    assert result.returncode == 0, result.stdout
    assert "PASS  no-pdfs" in result.stdout


def test_url_in_test_file_fails(repo: Path) -> None:
    _track(repo, "tests/unit/test_net.py", f'SITE = "{URL}"\n')
    result = _run_guard(repo)
    assert result.returncode != 0
    assert "FAIL  no-network-in-tests" in result.stdout
    assert "tests/unit/test_net.py" in result.stdout


@pytest.mark.parametrize(
    "relative", ["tests/fixtures/collect/fspo/urlmap.yaml", "tests/e2e/corpus.py"]
)
def test_url_allowed_in_url_maps_and_corpus(repo: Path, relative: str) -> None:
    _track(repo, relative, f"# {URL}\n")
    result = _run_guard(repo)
    assert result.returncode == 0, result.stdout
    assert "PASS  no-network-in-tests" in result.stdout


def test_removing_data_raw_from_gitignore_fails(repo: Path) -> None:
    gitignore = repo / ".gitignore"
    lines = gitignore.read_text(encoding="utf-8").splitlines()
    assert "data/raw/" in lines
    gitignore.write_text("\n".join(line for line in lines if line != "data/raw/") + "\n", "utf-8")

    result = _run_guard(repo)
    assert result.returncode != 0
    assert "FAIL  gitignore-covers-data" in result.stdout
    assert "data/raw/" in result.stdout


def test_missing_gitignore_fails(repo: Path) -> None:
    (repo / ".gitignore").unlink()
    result = _run_guard(repo)
    assert result.returncode != 0
    assert "FAIL  gitignore-covers-data" in result.stdout
    assert "mlruns/ is not ignored" in result.stdout
