"""Collector test setup: a temp data directory and a config with the source enabled."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from claimsense import config, paths
from claimsense.config import Config
from tests.collect.helpers import collect_patch


@pytest.fixture
def cioins_cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    """The resolved config for CIOINS collector tests.

    Data goes to a temp directory and an override file enables the source, so
    both the Python API and the command line (which calls ``config.load()``)
    see the same settings.
    """
    override = tmp_path / "collect-tests.yaml"
    override.write_text(yaml.safe_dump(collect_patch("cioins")), encoding="utf-8")
    monkeypatch.setenv(config.OVERRIDE_ENV_VAR, str(override))
    monkeypatch.setenv(paths.DATA_DIR_ENV_VAR, str(tmp_path / "data"))
    monkeypatch.delenv(paths.OUT_DIR_ENV_VAR, raising=False)
    return config.load()
