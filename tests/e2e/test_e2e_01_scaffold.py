"""E2E stage 01 (NFR-05, NFR-10): config, paths and package layout work together in the world."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys

import pytest

from claimsense import paths
from claimsense.schema import SOURCES
from tests.e2e import stages
from tests.e2e.conftest import E2EWorld

pytestmark = pytest.mark.e2e

SUBPACKAGES = (
    "collect",
    "parse",
    "label",
    "dataset",
    "models",
    "retrieve",
    "explain",
    "evaluate",
)


def test_world_paths_are_inside_root(world: E2EWorld) -> None:
    cfg = stages.run_scaffold(world)
    assert cfg == world.cfg

    assert world.root.is_dir()
    for name in (paths.DATA_DIR_ENV_VAR, paths.OUT_DIR_ENV_VAR):
        assert os.environ[name] == world.env[name]
        assert os.path.isdir(world.env[name])

    resolved = [
        paths.data_dir(),
        *(paths.raw_dir(source) for source in SOURCES),
        paths.interim_dir(),
        paths.processed_root(),
        paths.processed_dir("abc"),
        paths.models_dir(),
        paths.index_dir(),
        paths.reports_dir(),
    ]
    for path in resolved:
        assert path.is_relative_to(world.root), path
    assert paths.latest_processed() is None


def test_config_show_prints_world_paths(world: E2EWorld) -> None:
    stages.run_scaffold(world)
    result = subprocess.run(
        [sys.executable, "-m", "claimsense.config", "show"],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    for path in (paths.data_dir(), paths.models_dir(), paths.index_dir(), paths.reports_dir()):
        assert str(path) in result.stdout


def test_every_subpackage_imports(world: E2EWorld) -> None:
    stages.run_scaffold(world)
    for name in SUBPACKAGES:
        module = importlib.import_module(f"claimsense.{name}")
        assert module.__name__ == f"claimsense.{name}"
