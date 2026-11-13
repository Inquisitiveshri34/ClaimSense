"""Source registry (NFR-09, R2; terms-of-use-audit.md): countries, fixture policy, clearance."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from claimsense import config
from claimsense.collect.sources import (
    FIXTURE_POLICY_SAVED_ALLOWED,
    FIXTURE_POLICY_SYNTHETIC_ONLY,
    SOURCE_REGISTRY,
    SourceNotCleared,
    load_registry,
)
from claimsense.schema import COUNTRY_OF_SOURCE, SOURCES

pytestmark = pytest.mark.usefixtures("clean_env")

# The marker the docs use for a value nobody has verified yet (DATA_SOURCES.md).
UNKNOWN_LICENCE = "UNKNOWN — to verify"


def _source_patch(name: str, **changes: Any) -> dict[str, Any]:
    """A config patch for one source; ``enabled`` goes on the source, the rest on its audit."""
    section: dict[str, Any] = {}
    if "enabled" in changes:
        section["enabled"] = changes.pop("enabled")
    if changes:
        section["audit"] = changes
    return {"collect": {"sources": {name: section}}}


def _with(cfg: config.Config, patch: dict[str, Any]) -> config.Config:
    return config.Config.model_validate(config.deep_merge(cfg.model_dump(mode="json"), patch))


def test_registry_has_exactly_the_three_sources() -> None:
    registry = load_registry(config.load())

    assert tuple(registry) == SOURCES
    for name, info in registry.items():
        assert info.name == name
        assert info.country == COUNTRY_OF_SOURCE[name]
        assert info.robots_url.startswith(info.base_url)


@pytest.mark.parametrize("name", SOURCES)
def test_fixture_policy_follows_redistribution(name: str) -> None:
    base = config.load()

    closed = load_registry(_with(base, _source_patch(name, redistribution_allowed=False)))
    assert closed.fixture_policy(name) == "synthetic-or-redacted-only"
    assert closed.fixture_policy(name) == FIXTURE_POLICY_SYNTHETIC_ONLY

    open_ = load_registry(_with(base, _source_patch(name, redistribution_allowed=True)))
    assert open_.fixture_policy(name) == FIXTURE_POLICY_SAVED_ALLOWED


def test_fixture_policy_rejects_unknown_source() -> None:
    with pytest.raises(KeyError, match="unknown source"):
        load_registry(config.load()).fixture_policy("not-a-source")


def test_committed_config_enables_only_cleared_sources() -> None:
    cfg = config.load()
    registry = load_registry(cfg)  # would raise SourceNotCleared otherwise

    for name in SOURCES:
        if getattr(cfg.collect.sources, name).enabled:
            assert registry[name].licence_known, name


@pytest.mark.parametrize("name", SOURCES)
def test_enabled_source_with_unknown_licence_is_not_cleared(name: str) -> None:
    base = config.load()

    enabled = _with(base, _source_patch(name, enabled=True, licence=UNKNOWN_LICENCE))
    with pytest.raises(SourceNotCleared, match=name):
        load_registry(enabled)

    # The same unknown licence is fine while the source stays disabled.
    disabled = _with(base, _source_patch(name, enabled=False, licence=UNKNOWN_LICENCE))
    assert not load_registry(disabled)[name].licence_known


def test_empty_licence_counts_as_unknown() -> None:
    cfg = _with(config.load(), _source_patch(SOURCES[0], enabled=True, licence="  "))
    with pytest.raises(SourceNotCleared):
        load_registry(cfg)


def test_source_registry_follows_the_current_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert dict(SOURCE_REGISTRY) == dict(load_registry(config.load()))

    override = tmp_path / "override.yaml"
    patch = _source_patch(SOURCES[0], enabled=True, licence=UNKNOWN_LICENCE)
    override.write_text(yaml.safe_dump(patch), encoding="utf-8")
    monkeypatch.setenv(config.OVERRIDE_ENV_VAR, str(override))

    with pytest.raises(SourceNotCleared, match=SOURCES[0]):
        len(SOURCE_REGISTRY)
