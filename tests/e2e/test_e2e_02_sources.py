"""E2E stage 02 (NFR-08, NFR-09, risk R2): the world's sources are enabled, cleared and hashed."""

from __future__ import annotations

import pytest

from claimsense import config
from claimsense.collect.sources import SOURCE_REGISTRY
from claimsense.schema import COUNTRY_OF_SOURCE, SOURCES
from tests.e2e import stages
from tests.e2e.conftest import E2EWorld

pytestmark = pytest.mark.e2e


def test_world_enables_and_clears_every_source(world: E2EWorld) -> None:
    registry = stages.run_sources(world)  # raises SourceNotCleared if the override is incomplete

    assert tuple(registry) == SOURCES
    for name in SOURCES:
        assert getattr(world.cfg.collect.sources, name).enabled, name
        assert registry[name].licence_known, name
        assert registry[name].country == COUNTRY_OF_SOURCE[name]

    # What the collectors (PRs 3-4) need from this stage.
    assert world.cfg.collect.contact_email
    assert world.cfg.collect.min_interval_s >= config.MIN_INTERVAL_FLOOR_S
    # The default registry follows the world's config too.
    assert dict(SOURCE_REGISTRY) == dict(registry)


def test_world_config_hash_differs_from_repo(
    world: E2EWorld, monkeypatch: pytest.MonkeyPatch
) -> None:
    stages.run_sources(world)
    world_hash = config.config_hash(world.cfg)

    monkeypatch.delenv(config.OVERRIDE_ENV_VAR)
    repo_cfg = config.load()

    # The world enables sources the repo config leaves disabled; `enabled` is a V key.
    assert repo_cfg.collect.sources != world.cfg.collect.sources
    assert config.config_hash(repo_cfg) != world_hash
