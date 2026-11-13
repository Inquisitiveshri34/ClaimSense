"""Shared helpers for collector tests (PR 3; reused by the FOS and FSPO tests in PR 4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from claimsense import config
from claimsense.collect.base import Collector, PoliteSession, RunStats
from claimsense.collect.manifest import Manifest, manifest_path
from claimsense.config import Config
from tests.stubs.fake_clock import FakeClock
from tests.stubs.fake_http import FakeTransport

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "collect"

# Values for tests only; they say nothing about a real publisher.
TEST_CONTACT_EMAIL = "collector-tests@example.invalid"
TEST_LICENCE = "collector tests (synthetic fixtures)"


def collect_patch(source: str, **collect_overrides: Any) -> dict[str, Any]:
    """A config override that enables ``source`` for tests and sets a test contact email."""
    return {
        "collect": {
            "contact_email": TEST_CONTACT_EMAIL,
            **collect_overrides,
            "sources": {source: {"enabled": True, "audit": {"licence": TEST_LICENCE}}},
        }
    }


def collect_config(source: str, **collect_overrides: Any) -> Config:
    """The current config with ``source`` enabled for tests and a test contact email."""
    patch = collect_patch(source, **collect_overrides)
    return Config.model_validate(config.deep_merge(config.load().model_dump(mode="json"), patch))


def base_url(cfg: Config, source: str) -> str:
    """The site root of a source, from the config (test files hold no URLs)."""
    return getattr(cfg.collect.sources, source).audit.base_url


def robots_url(cfg: Config, source: str) -> str:
    """The robots.txt URL of a source, from the config."""
    return getattr(cfg.collect.sources, source).audit.robots_url


def scenario(name: str) -> list[str]:
    """One error-response scenario from ``fixtures/collect/http/responses.yaml``."""
    scenarios = yaml.safe_load((FIXTURES / "http" / "responses.yaml").read_text("utf-8"))
    return list(scenarios[name])


def crawl_delay_in(robots_file: Path) -> float:
    """The ``Crawl-delay`` value written in a robots.txt fixture."""
    for line in robots_file.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition(":")
        if key.strip().lower() == "crawl-delay":
            return float(value)
    raise ValueError(f"no Crawl-delay in {robots_file}")


def gaps(transport: FakeTransport) -> list[float]:
    """Seconds between each request and the one before it."""
    times = [request.timestamp for request in transport.requests]
    return [later - earlier for earlier, later in zip(times, times[1:], strict=False)]


def assert_polite(transport: FakeTransport, cfg: Config, min_gap: float | None = None) -> None:
    """NFR-08 on a finished run: spacing, one connection, identified User-Agent."""
    floor = cfg.collect.min_interval_s if min_gap is None else min_gap
    assert transport.requests, "no request was made"
    assert all(gap >= floor for gap in gaps(transport)), gaps(transport)
    assert transport.max_in_flight == 1
    for request in transport.requests:
        agent = request.headers["User-Agent"]
        assert cfg.project.version in agent
        assert cfg.collect.contact_email in agent


def session_on(
    cfg: Config, urlmap: dict[str, Any], root: Path, clock: FakeClock | None = None
) -> tuple[PoliteSession, FakeTransport, FakeClock]:
    """A polite session wired to a fake site described by ``urlmap``."""
    clock = clock if clock is not None else FakeClock()
    transport = FakeTransport(urlmap, root, clock)
    return PoliteSession(cfg, transport=transport, clock=clock), transport, clock


def run_collector(
    collector_class: type[Collector],
    cfg: Config,
    urlmap: Path | dict[str, Any],
    *,
    root: Path | None = None,
    clock: FakeClock | None = None,
    crash_after: int | None = None,
    **run_arguments: Any,
) -> tuple[RunStats, FakeTransport]:
    """Run a collector once against a fake site and return its stats and the transport.

    ``urlmap`` is a ``urlmap.yaml`` path, or a dict with ``root`` as the folder its files are in.
    The manifest is the one ``cfg`` points at, so calling this twice is a re-run.
    """
    clock = clock if clock is not None else FakeClock()
    if isinstance(urlmap, Path):
        transport = FakeTransport.from_urlmap(urlmap, clock)
    else:
        assert root is not None, "a dict urlmap needs the folder its files are in"
        transport = FakeTransport(urlmap, root, clock)
    if crash_after is not None:
        transport.crash_after(crash_after)
    session = PoliteSession(
        cfg, transport=transport, clock=clock, dry_run=bool(run_arguments.get("dry_run"))
    )
    with Manifest(manifest_path(cfg)) as manifest:
        stats = collector_class(cfg, session, manifest, clock=clock).run(**run_arguments)
    return stats, transport


def flip_first_byte(path: Path) -> None:
    """Change one byte of a file in place."""
    data = bytearray(path.read_bytes())
    data[0] ^= 0xFF
    path.write_bytes(bytes(data))
