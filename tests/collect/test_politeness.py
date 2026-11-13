"""Polite session (NFR-08; collection-runbook.md §4, §7): spacing, robots, retries, hard stops."""

from __future__ import annotations

from pathlib import Path

import pytest

from claimsense.collect.base import (
    ContactEmailMissing,
    DisallowedByRobots,
    FetchFailed,
    PoliteSession,
    StopCollection,
)
from claimsense.collect.manifest import PARTIAL_DIRNAME
from claimsense.config import Config
from tests.collect.helpers import (
    FIXTURES,
    assert_polite,
    base_url,
    collect_config,
    crawl_delay_in,
    gaps,
    robots_url,
    scenario,
    session_on,
)
from tests.stubs.fake_clock import FakeClock
from tests.stubs.fake_http import FakeTransport, UnmappedURL

pytestmark = pytest.mark.usefixtures("clean_env")

SOURCE = "cioins"
HTTP = FIXTURES / "http"
NO_ROBOTS = "@404"


@pytest.fixture
def cfg() -> Config:
    return collect_config(SOURCE)


def _site(cfg: Config, pages: dict[str, object], robots: object = NO_ROBOTS) -> dict[str, object]:
    """A URL map: ``pages`` keyed by path under the source's site root, plus robots.txt."""
    root = base_url(cfg, SOURCE)
    return {robots_url(cfg, SOURCE): robots, **{f"{root}/{path}": v for path, v in pages.items()}}


def _url(cfg: Config, path: str) -> str:
    return f"{base_url(cfg, SOURCE)}/{path}"


def test_requests_are_spaced_by_min_interval(cfg: Config) -> None:
    pages = {f"page-{n}": "body.txt" for n in range(5)}
    session, transport, _ = session_on(cfg, _site(cfg, pages), HTTP)

    for path in pages:
        session.get(_url(cfg, path))

    assert len(transport.requests) == len(pages) + 1  # robots.txt first
    assert transport.requests[0].url == robots_url(cfg, SOURCE)
    assert_polite(transport, cfg)
    assert max(gaps(transport)) <= cfg.collect.min_interval_s + cfg.collect.jitter_s


def test_robots_crawl_delay_raises_the_gap(cfg: Config) -> None:
    robots_file = FIXTURES / SOURCE / "robots.txt"
    delay = crawl_delay_in(robots_file)
    assert delay > cfg.collect.min_interval_s, "the fixture must state a longer delay than config"
    urlmap = _site(cfg, {"a": "body.txt", "b": "body.txt"}, robots=str(robots_file))
    session, transport, _ = session_on(cfg, urlmap, HTTP)

    session.get(_url(cfg, "a"))
    session.get(_url(cfg, "b"))

    assert session.crawl_delay(_url(cfg, "a")) == delay
    assert_polite(transport, cfg, min_gap=delay)


def test_robots_disallowed_path_is_never_requested(cfg: Config) -> None:
    robots_file = FIXTURES / SOURCE / "robots.txt"
    urlmap = _site(cfg, {"admin/secret": "body.txt"}, robots=str(robots_file))
    session, transport, _ = session_on(cfg, urlmap, HTTP)

    with pytest.raises(DisallowedByRobots):
        session.get(_url(cfg, "admin/secret"))
    assert transport.urls() == [robots_url(cfg, SOURCE)]


def test_only_one_request_in_flight(cfg: Config) -> None:
    pages = {f"page-{n}": "body.txt" for n in range(3)}
    session, transport, _ = session_on(cfg, _site(cfg, pages), HTTP)
    for path in pages:
        session.get(_url(cfg, path))
    assert transport.max_in_flight == 1


def test_user_agent_names_version_and_contact(cfg: Config) -> None:
    session, transport, _ = session_on(cfg, _site(cfg, {"a": "body.txt"}), HTTP)
    session.get(_url(cfg, "a"))

    assert cfg.project.version in session.user_agent
    assert cfg.collect.contact_email in session.user_agent
    assert {r.headers["User-Agent"] for r in transport.requests} == {session.user_agent}


def test_429_waits_for_retry_after(cfg: Config) -> None:
    responses = scenario("rate_limited_with_retry_after")
    retry_after = float(responses[0].rpartition(":")[2])
    session, transport, _ = session_on(cfg, _site(cfg, {"a": responses}), HTTP)

    response = session.get(_url(cfg, "a"))

    assert response.status == 200
    assert gaps(transport)[-1] >= retry_after
    assert_polite(transport, cfg)


@pytest.mark.parametrize(
    "name", ["unavailable_without_retry_after", "rate_limited_without_retry_after"]
)
def test_503_or_429_without_header_backs_off(cfg: Config, name: str) -> None:
    session, transport, _ = session_on(cfg, _site(cfg, {"a": scenario(name)}), HTTP)

    assert session.get(_url(cfg, "a")).status == 200
    assert gaps(transport)[-1] >= cfg.collect.retry_after_default_s


@pytest.mark.parametrize("name", ["timeout_then_ok", "server_error_then_ok", "truncated_then_ok"])
def test_transient_failure_is_retried_with_backoff(cfg: Config, name: str) -> None:
    session, transport, _ = session_on(cfg, _site(cfg, {"a": scenario(name)}), HTTP)

    assert session.get(_url(cfg, "a")).status == 200
    assert transport.urls().count(_url(cfg, "a")) == 2
    assert gaps(transport)[-1] >= cfg.collect.backoff_base_s


def test_403_stops_the_run(cfg: Config) -> None:
    urlmap = _site(cfg, {"a": scenario("forbidden"), "b": "body.txt"})
    session, transport, _ = session_on(cfg, urlmap, HTTP)

    with pytest.raises(StopCollection, match="403"):
        session.get(_url(cfg, "a"))
    assert transport.urls().count(_url(cfg, "a")) == 1  # never retried


def test_404_fails_once_without_retry(cfg: Config) -> None:
    session, transport, _ = session_on(cfg, _site(cfg, {"a": scenario("not_found")}), HTTP)

    with pytest.raises(FetchFailed, match="404"):
        session.get(_url(cfg, "a"))
    assert transport.urls().count(_url(cfg, "a")) == 1


def test_consecutive_failures_stop_the_run(cfg: Config) -> None:
    limit = cfg.collect.stop_after_consecutive_failures
    pages = {f"gone-{n}": scenario("not_found") for n in range(limit + 5)}
    session, transport, _ = session_on(cfg, _site(cfg, pages, robots="body.txt"), HTTP)

    failed = 0
    with pytest.raises(StopCollection, match="consecutive failures"):
        for path in pages:
            try:
                session.get(_url(cfg, path))
            except FetchFailed:
                failed += 1

    assert failed == limit - 1  # the failure that reaches the limit stops the run
    assert len(transport.requests) == limit + 1  # robots.txt, then `limit` failures
    assert_polite(transport, cfg)


def test_a_success_resets_the_failure_count(cfg: Config) -> None:
    limit = cfg.collect.stop_after_consecutive_failures
    pages: dict[str, object] = {}
    for n in range(limit + 5):
        pages[f"gone-{n}"] = scenario("not_found")
        pages[f"ok-{n}"] = "body.txt"
    session, _, _ = session_on(cfg, _site(cfg, pages), HTTP)

    for path in pages:
        try:
            session.get(_url(cfg, path))
        except FetchFailed:
            pass  # never StopCollection: failures are not consecutive


def test_retries_are_bounded(cfg: Config) -> None:
    patient = collect_config(SOURCE, stop_after_consecutive_failures=100)
    urlmap = _site(patient, {"a": scenario("always_timeout")})
    session, transport, _ = session_on(patient, urlmap, HTTP)

    with pytest.raises(FetchFailed, match="retries"):
        session.get(_url(patient, "a"))
    assert transport.urls().count(_url(patient, "a")) == patient.collect.max_retries + 1


def test_truncated_download_leaves_only_a_partial_file(cfg: Config, tmp_path: Path) -> None:
    urlmap = _site(cfg, {"doc.txt": scenario("always_truncated")})
    session, _, _ = session_on(cfg, urlmap, HTTP)
    dest = tmp_path / "raw" / "doc.txt"

    with pytest.raises(FetchFailed, match="truncated"):
        session.download(_url(cfg, "doc.txt"), dest)

    assert not dest.exists()
    assert [p.name for p in (dest.parent / PARTIAL_DIRNAME).iterdir()] == ["doc.txt"]


def test_download_writes_file_and_returns_sha256(cfg: Config, tmp_path: Path) -> None:
    from claimsense.collect.manifest import sha256_file

    session, _, _ = session_on(cfg, _site(cfg, {"doc.txt": "body.txt"}), HTTP)
    dest = tmp_path / "raw" / "doc.txt"

    digest = session.download(_url(cfg, "doc.txt"), dest)

    assert dest.read_bytes() == (HTTP / "body.txt").read_bytes()
    assert digest == sha256_file(dest)
    assert not any((dest.parent / PARTIAL_DIRNAME).iterdir())


def test_empty_contact_email_refuses_to_start() -> None:
    anonymous = collect_config(SOURCE, contact_email="")
    transport = FakeTransport({}, HTTP, FakeClock())

    with pytest.raises(ContactEmailMissing):
        PoliteSession(anonymous, transport=transport, clock=FakeClock())
    # A dry run may start without one.
    PoliteSession(anonymous, transport=transport, clock=FakeClock(), dry_run=True)


def test_unmapped_url_fails_loudly(cfg: Config) -> None:
    session, _, _ = session_on(cfg, _site(cfg, {}), HTTP)
    with pytest.raises(UnmappedURL):
        session.get(_url(cfg, "not-in-the-map"))
