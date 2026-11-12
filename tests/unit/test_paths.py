"""Path helpers (NFR-05; configuration.md §5.2, dataset-versioning.md §1): defaults, overrides."""

from __future__ import annotations

from pathlib import Path

import pytest

from claimsense import config, paths
from claimsense.schema import SOURCES

pytestmark = pytest.mark.usefixtures("clean_env")


def _data_paths() -> list[Path]:
    return [
        paths.data_dir(),
        *(paths.raw_dir(source) for source in SOURCES),
        paths.interim_dir(),
        paths.processed_root(),
        paths.processed_dir("abc"),
    ]


def _out_paths() -> list[Path]:
    return [paths.models_dir(), paths.index_dir(), paths.reports_dir()]


def test_defaults_resolve_under_repo_root() -> None:
    root = config.repo_root()
    for path in _data_paths() + _out_paths():
        assert path.is_relative_to(root), path


def test_data_dir_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(paths.DATA_DIR_ENV_VAR, str(tmp_path))
    target = tmp_path.resolve()

    assert paths.data_dir() == target
    for path in _data_paths():
        assert path.is_relative_to(target), path
    for path in _out_paths():
        assert not path.is_relative_to(target), path


def test_out_dir_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(paths.OUT_DIR_ENV_VAR, str(tmp_path))
    target = tmp_path.resolve()

    for path in _out_paths():
        assert path.is_relative_to(target), path
    for path in _data_paths():
        assert not path.is_relative_to(target), path


def test_processed_dir_naming() -> None:
    # dataset-versioning.md §1: the directory is "v" + hash, under processed/.
    with_prefix = paths.processed_dir("vabc")
    without_prefix = paths.processed_dir("abc")

    assert without_prefix == with_prefix
    assert with_prefix.parts[-2:] == ("processed", "vabc")
    assert with_prefix.parent == paths.processed_root()


def test_latest_processed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(paths.DATA_DIR_ENV_VAR, str(tmp_path))
    assert paths.latest_processed() is None

    paths.processed_root().mkdir(parents=True)
    (paths.processed_root() / paths.LATEST_FILENAME).write_text("vabc\n", encoding="utf-8")
    assert paths.latest_processed() == paths.processed_dir("vabc")


def test_raw_dir_rejects_unknown_source() -> None:
    with pytest.raises(ValueError, match="unknown source"):
        paths.raw_dir("not-a-source")
