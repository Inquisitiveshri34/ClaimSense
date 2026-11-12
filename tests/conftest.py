"""Shared test setup (NFR-05, NFR-10): config loader, seeds, network block, local_data skip."""

from __future__ import annotations

import importlib.util
import os
import random
import socket
import warnings
from pathlib import Path

import pytest
from pytest_socket import SocketBlockedError

from claimsense import config, paths
from claimsense.config import Config

# Read once, before any test or fixture can change the environment.
RUNNING_IN_CI = os.environ.get("CLAIMSENSE_ENV") == "ci"

# Reason text fixed by docs/testing/test-strategy.md §4.
LOCAL_DATA_SKIP_REASON = "data/processed/ not present — run make build first"

# Environment variables that change what config and paths resolve to.
RESOLUTION_ENV_VARS = (
    config.OVERRIDE_ENV_VAR,
    paths.DATA_DIR_ENV_VAR,
    paths.OUT_DIR_ENV_VAR,
)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip ``local_data`` tests when there is no dataset, and run e2e tests last."""
    local_data_items = [item for item in items if item.get_closest_marker("local_data")]
    if local_data_items and paths.latest_processed() is None:
        skip = pytest.mark.skip(reason=LOCAL_DATA_SKIP_REASON)
        for item in local_data_items:
            item.add_marker(skip)

    # The e2e `world` fixture changes the environment for the rest of the
    # session, so in a mixed run the e2e tests go after everything else.
    e2e_dir = Path(__file__).parent / "e2e"
    items.sort(key=lambda item: e2e_dir in item.path.parents)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove the variables that redirect config and paths, for tests of the defaults."""
    for name in RESOLUTION_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def cfg() -> Config:
    """The resolved configuration, exactly as the code under test loads it."""
    return config.load()


@pytest.fixture(autouse=True)
def _seed_everything(cfg: Config) -> None:
    """Seed every random generator from ``project.seed`` before each test."""
    random.seed(cfg.project.seed)
    if importlib.util.find_spec("numpy") is not None:
        import numpy as np

        np.random.seed(cfg.project.seed)


@pytest.fixture(autouse=True)
def _network_blocked_in_ci() -> None:
    """In CI mode, fail any test that runs without the pytest-socket network block."""
    if not RUNNING_IN_CI:
        return
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # pytest-socket warns on every blocked attempt
            probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except SocketBlockedError:
        return
    probe.close()
    pytest.fail("CLAIMSENSE_ENV=ci but sockets are not blocked; run pytest with --disable-socket")
