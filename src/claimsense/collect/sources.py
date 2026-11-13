"""The source registry: what may be collected from each ombudsman, and on what terms.

One ``SourceInfo`` per source, built from ``collect.sources.<name>.audit`` in
the config (the machine-readable copy of the decision table in
``DATA_SOURCES.md`` and ``docs/data/terms-of-use-audit.md``) and the country in
``claimsense.schema``. A source that is enabled while its licence is still
unknown stops the registry from loading (NFR-09, risk R2).

This module holds decisions only. It contains no network code.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import date

from claimsense import config
from claimsense.config import Config
from claimsense.schema import COUNTRY_OF_SOURCE, SOURCES

# A licence that starts with this word has not been established yet. The docs
# write it as "UNKNOWN — to verify".
UNKNOWN_PREFIX = "UNKNOWN"

# Which kinds of fixture may be committed for a source (docs/testing/test-fixtures.md §2).
FIXTURE_POLICY_SAVED_ALLOWED = "saved-allowed"
FIXTURE_POLICY_SYNTHETIC_ONLY = "synthetic-or-redacted-only"


class SourceNotCleared(RuntimeError):
    """A source is enabled in the config but its licence is still unknown."""


@dataclass(frozen=True)
class SourceInfo:
    """The audit decision for one source.

    Attributes:
        name: Source key, one of ``claimsense.schema.SOURCES``.
        country: ISO 3166-1 alpha-2 country of the ombudsman.
        base_url: Root URL of the publisher's site.
        robots_url: URL of the site's robots.txt.
        licence: Terms under which ClaimSense may use the decisions, or a
            value starting with ``UNKNOWN`` while that is not established.
        redistribution_allowed: Whether derived, anonymised text may be published.
        audit_date: Day the terms were last read.
    """

    name: str
    country: str
    base_url: str
    robots_url: str
    licence: str
    redistribution_allowed: bool
    audit_date: date

    @property
    def licence_known(self) -> bool:
        """Whether a licence has been established for this source."""
        licence = self.licence.strip()
        return bool(licence) and not licence.upper().startswith(UNKNOWN_PREFIX)


class SourceRegistry(Mapping[str, SourceInfo]):
    """A read-only mapping from source name to ``SourceInfo``."""

    def __init__(self, infos: Iterable[SourceInfo]) -> None:
        self._infos = {info.name: info for info in infos}

    def _sources(self) -> dict[str, SourceInfo]:
        return self._infos

    def __getitem__(self, name: str) -> SourceInfo:
        sources = self._sources()
        if name not in sources:
            raise KeyError(f"unknown source {name!r}; expected one of {tuple(sources)}")
        return sources[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._sources())

    def __len__(self) -> int:
        return len(self._sources())

    def fixture_policy(self, name: str) -> str:
        """Return which fixtures may be committed for a source.

        ``"saved-allowed"`` if derived text of the source may be redistributed;
        otherwise ``"synthetic-or-redacted-only"``: no real document of that
        source goes into the repo.
        """
        if self[name].redistribution_allowed:
            return FIXTURE_POLICY_SAVED_ALLOWED
        return FIXTURE_POLICY_SYNTHETIC_ONLY


def load_registry(cfg: Config | None = None) -> SourceRegistry:
    """Build the registry from a config.

    Args:
        cfg: The config to read. Defaults to the current resolved config.

    Raises:
        SourceNotCleared: A source has ``enabled: true`` while its licence is unknown.
    """
    cfg = cfg if cfg is not None else config.load()
    infos: list[SourceInfo] = []
    not_cleared: list[str] = []
    for name in SOURCES:
        section = getattr(cfg.collect.sources, name)
        audit = section.audit
        info = SourceInfo(
            name=name,
            country=COUNTRY_OF_SOURCE[name],
            base_url=audit.base_url,
            robots_url=audit.robots_url,
            licence=audit.licence,
            redistribution_allowed=audit.redistribution_allowed,
            audit_date=audit.audit_date,
        )
        if section.enabled and not info.licence_known:
            not_cleared.append(name)
        infos.append(info)
    if not_cleared:
        names = ", ".join(not_cleared)
        raise SourceNotCleared(
            f"enabled but not cleared: {names}. Record the licence in "
            "collect.sources.<name>.audit.licence (and DATA_SOURCES.md) or set enabled: false."
        )
    return SourceRegistry(infos)


class _CurrentConfigRegistry(SourceRegistry):
    """A registry that is rebuilt from the current resolved config on every use."""

    def __init__(self) -> None:
        super().__init__(())

    def _sources(self) -> dict[str, SourceInfo]:
        return load_registry()._sources()


# The registry for the current resolved config. It follows CLAIMSENSE_CONFIG, so
# it raises SourceNotCleared on use, not on import. Code that already holds a
# config should call ``load_registry(cfg)`` once instead.
SOURCE_REGISTRY: SourceRegistry = _CurrentConfigRegistry()
