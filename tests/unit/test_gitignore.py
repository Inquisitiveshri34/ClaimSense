"""Ignore rules (NFR-09c, risks R2, R5; ci-cd.md §3.4): data, runs and secrets cannot be added."""

from __future__ import annotations

import subprocess

import pytest

from claimsense import config

IGNORED = [
    "data/raw/a.pdf",
    "data/interim/a.json",
    "data/processed/v1/train.parquet",
    "data/cache/x",
    "data/manifests/m.sqlite",
    "mlruns/0/meta.yaml",
    ".env",
]

NOT_IGNORED = ["data/README.md", "data/.gitkeep"]


def _is_ignored(path: str) -> bool:
    """Ask git whether the repo's ignore rules match ``path`` (tracked or not)."""
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--no-index", "--", path],
        cwd=config.repo_root(),
    )
    assert result.returncode in (0, 1), f"git check-ignore failed for {path}"
    return result.returncode == 0


@pytest.mark.parametrize("path", IGNORED)
def test_path_is_ignored(path: str) -> None:
    assert _is_ignored(path)


@pytest.mark.parametrize("path", NOT_IGNORED)
def test_path_is_not_ignored(path: str) -> None:
    assert not _is_ignored(path)
