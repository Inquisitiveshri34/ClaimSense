"""Shared collector machinery: the polite session and the resumable run loop.

``PoliteSession`` is the only place a request is made from. It enforces NFR-08
(``docs/data/collection-runbook.md`` §4): one request at a time, a minimum
interval between requests, an identified User-Agent, robots.txt, bounded
retries and a hard stop. ``Collector`` is the run loop every source shares
(runbook §5): skip what is already held, filter, download, detect duplicates,
write the manifest. A source only has to say which documents its site lists.

The transport and the clock are constructor arguments, so tests run on a fake
site and a fake clock with no network and no waiting.
"""

from __future__ import annotations

import hashlib
import random
import shutil
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import ClassVar, Protocol
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from claimsense import __version__, paths
from claimsense.collect.manifest import (
    PARTIAL_DIRNAME,
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STATUS_FILTERED,
    STATUS_STORED,
    CrawlEntry,
    Manifest,
    ManifestRow,
    raw_root,
    sha256_file,
)
from claimsense.collect.sources import load_registry
from claimsense.collect.transport import RequestsTransport, Response, Transport, TransportError
from claimsense.config import Config

ROBOTS_PATH = "/robots.txt"
RETRY_AFTER_STATUSES = (429, 503)


class CollectionError(Exception):
    """Base class for every error a collector raises on purpose."""


class StopCollection(CollectionError):
    """The run must stop now (blocked, or too many consecutive failures). Never worked around."""


class FetchFailed(CollectionError):
    """One URL could not be fetched; the run goes on with the next document."""

    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"{reason}: {url}")
        self.url = url
        self.reason = reason


class DisallowedByRobots(FetchFailed):
    """The site's robots.txt disallows this path; it was not requested."""

    def __init__(self, url: str) -> None:
        super().__init__(url, "disallowed by robots.txt")


class ContactEmailMissing(CollectionError):
    """``collect.contact_email`` is empty; a live run must identify who is asking."""


class SourceDisabled(CollectionError):
    """The source has ``enabled: false`` in the config; it is not cleared for collection."""


class Clock(Protocol):
    """Time as the session sees it; replaced by a fake clock in tests."""

    def monotonic(self) -> float:
        """Seconds from an arbitrary start, never going backwards."""
        ...

    def sleep(self, seconds: float) -> None:
        """Wait for ``seconds``."""
        ...

    def now(self) -> datetime:
        """The current UTC time."""
        ...


class SystemClock:
    """The real clock."""

    def monotonic(self) -> float:
        """See ``Clock.monotonic``."""
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        """See ``Clock.sleep``."""
        time.sleep(seconds)

    def now(self) -> datetime:
        """See ``Clock.now``."""
        return datetime.now(UTC)


@dataclass
class PartialDownload:
    """A fetched document waiting in the partial folder until the collector accepts it."""

    path: Path
    dest: Path
    sha256: str
    mime_type: str

    def commit(self) -> Path:
        """Move the file into place (atomic rename) and return its final path."""
        self.dest.parent.mkdir(parents=True, exist_ok=True)
        self.path.replace(self.dest)
        return self.dest

    def discard(self) -> None:
        """Delete the partial file."""
        self.path.unlink(missing_ok=True)


class PoliteSession:
    """The single, rate-limited connection a collector uses.

    Args:
        cfg: Resolved config; the ``collect`` section sets every limit.
        transport: Performs the requests. Defaults to ``RequestsTransport``.
        clock: Supplies time and sleep. Defaults to the system clock.
        dry_run: A dry run may start without a contact email.

    Raises:
        ContactEmailMissing: ``collect.contact_email`` is empty and this is not a dry run.
    """

    def __init__(
        self,
        cfg: Config,
        transport: Transport | None = None,
        clock: Clock | None = None,
        *,
        dry_run: bool = False,
    ) -> None:
        collect = cfg.collect
        if not dry_run and not collect.contact_email.strip():
            raise ContactEmailMissing(
                "collect.contact_email is empty. Set it in a local override file "
                "(configs/local.yaml) before any live run."
            )
        self._collect = collect
        self._transport = transport if transport is not None else RequestsTransport()
        self._clock = clock if clock is not None else SystemClock()
        self.user_agent = collect.user_agent.format(
            version=cfg.project.version, contact_email=collect.contact_email
        )
        # The product token robots.txt rules are matched against, e.g. "ClaimSense".
        self._robots_agent = self.user_agent.split("/", 1)[0].strip()
        self._rng = random.Random(cfg.project.seed)
        self._robots: dict[str, RobotFileParser | None] = {}
        self._last_request_at: float | None = None
        self._consecutive_failures = 0
        self.requests_made = 0

    # --- public ---------------------------------------------------------------

    def get(self, url: str) -> Response:
        """Fetch a page politely and return the successful response.

        Raises:
            DisallowedByRobots: robots.txt disallows the path; no request was made.
            FetchFailed: The URL could not be fetched (for example 404, or retries used up).
            StopCollection: The run must stop (403, or too many consecutive failures).
        """
        self._check_robots(url)
        return self._fetch(url, sink=None)

    def download_partial(self, url: str, dest: Path) -> PartialDownload:
        """Fetch a document into ``<dest folder>/.partial/`` and hash it, without placing it.

        The caller decides whether to ``commit()`` it to ``dest`` or ``discard()`` it.
        Raises the same errors as ``get``.
        """
        self._check_robots(url)
        partial = dest.parent / PARTIAL_DIRNAME / dest.name
        partial.parent.mkdir(parents=True, exist_ok=True)
        response = self._fetch(url, sink=partial)
        mime_type = response.headers.get("content-type", "").split(";")[0].strip()
        return PartialDownload(
            path=partial,
            dest=dest,
            sha256=hashlib.sha256(response.content).hexdigest(),
            mime_type=mime_type or "application/octet-stream",
        )

    def download(self, url: str, dest: Path) -> str:
        """Fetch a document to ``dest`` (partial file, then atomic rename); return its SHA-256."""
        partial = self.download_partial(url, dest)
        partial.commit()
        return partial.sha256

    def crawl_delay(self, url: str) -> float:
        """Seconds between requests to this URL's host: the larger of config and robots.txt."""
        robots = self._robots.get(_origin(url))
        stated = robots.crawl_delay(self._robots_agent) if robots is not None else None
        return max(self._collect.min_interval_s, float(stated or 0))

    # --- robots ---------------------------------------------------------------

    def _check_robots(self, url: str) -> None:
        origin = _origin(url)
        if origin not in self._robots:
            self._robots[origin] = self._load_robots(origin)
        robots = self._robots[origin]
        if robots is not None and not robots.can_fetch(self._robots_agent, url):
            raise DisallowedByRobots(url)

    def _load_robots(self, origin: str) -> RobotFileParser | None:
        """Fetch and parse the host's robots.txt; ``None`` means none is published."""
        try:
            response = self._fetch(origin + ROBOTS_PATH, sink=None)
        except FetchFailed as exc:
            if exc.reason.startswith("HTTP 4"):
                return None  # not published: recorded as "none", never as permission
            raise StopCollection(f"robots.txt could not be read ({exc.reason})") from exc
        parser = RobotFileParser()
        parser.parse(response.content.decode("utf-8", errors="replace").splitlines())
        return parser

    # --- one URL, with waits and retries --------------------------------------

    def _fetch(self, url: str, sink: Path | None) -> Response:
        collect = self._collect
        extra_wait = 0.0
        reason = "no attempt made"
        for attempt in range(collect.max_retries + 1):
            self._wait_for_turn(url, extra_wait)
            try:
                response = self._transport.get(
                    url, {"User-Agent": self.user_agent}, collect.timeout_s
                )
            except TransportError as exc:
                self._request_done()
                reason = f"{type(exc).__name__}: {exc}"
                extra_wait = collect.backoff_base_s * 2**attempt
                self._count_failure(reason)
                continue
            self._request_done()

            if sink is not None and response.status == 200:
                sink.write_bytes(response.content)
            if response.status == 200 and not response.truncated:
                self._consecutive_failures = 0
                return response

            if response.status == 403:
                raise StopCollection(
                    f"HTTP 403 for {url}. Stop: do not change the User-Agent or retry. "
                    "Re-check robots.txt and contact the publisher (runbook §7)."
                )
            reason = "truncated body" if response.status == 200 else f"HTTP {response.status}"
            self._count_failure(reason)
            if response.status in RETRY_AFTER_STATUSES:
                extra_wait = self._retry_after(response)
            elif response.status == 200 or response.status >= 500:
                extra_wait = collect.backoff_base_s * 2**attempt
            else:
                raise FetchFailed(url, reason)  # other 4xx, e.g. 404: retrying cannot help
        raise FetchFailed(url, f"{reason} after {collect.max_retries} retries")

    def _wait_for_turn(self, url: str, extra_wait: float) -> None:
        """Sleep until this request may be sent."""
        wait = extra_wait
        if self._last_request_at is not None:
            gap = self.crawl_delay(url) + self._rng.uniform(0, self._collect.jitter_s)
            elapsed = self._clock.monotonic() - self._last_request_at
            wait = max(wait, gap - elapsed)
        if wait > 0:
            self._clock.sleep(wait)

    def _request_done(self) -> None:
        self.requests_made += 1
        self._last_request_at = self._clock.monotonic()

    def _count_failure(self, reason: str) -> None:
        self._consecutive_failures += 1
        limit = self._collect.stop_after_consecutive_failures
        if self._consecutive_failures >= limit:
            raise StopCollection(f"{limit} consecutive failures (last: {reason})")

    def _retry_after(self, response: Response) -> float:
        """Seconds to wait after a 429/503: the ``Retry-After`` header, else the config default."""
        value = response.headers.get("retry-after", "").strip()
        if value.isdigit():
            return float(value)
        if value:
            try:
                until = parsedate_to_datetime(value)
            except (TypeError, ValueError):
                until = None
            if until is not None:
                if until.tzinfo is None:
                    until = until.replace(tzinfo=UTC)
                return max(0.0, (until - self._clock.now()).total_seconds())
        return self._collect.retry_after_default_s


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


@dataclass(frozen=True)
class ListedDoc:
    """One document a source's listing offers.

    Attributes:
        doc_id: Stable, source-prefixed identifier.
        url: Absolute URL of the document.
        decision_date: Date of the decision.
        insurer: Insurer name as listed.
        product_listed: The policy or product type exactly as the listing words it.
        product: The matching health product, or ``None`` if this is not a health decision.
        office: Ombudsman office (CIOINS only).
        outcome_raw: The source's outcome wording if the listing gives one, else empty.
        extension: File extension to store the document under.
    """

    doc_id: str
    url: str
    decision_date: date
    insurer: str
    product_listed: str
    product: str | None
    office: str | None = None
    outcome_raw: str = ""
    extension: str = "pdf"


@dataclass
class RunStats:
    """What one collector run did. ``stopped`` holds the reason if the run stopped early."""

    source: str
    dry_run: bool = False
    listed: int = 0
    stored: int = 0
    filtered: int = 0
    duplicate: int = 0
    failed: int = 0
    skipped: int = 0
    elapsed_s: float = 0.0
    stopped: str | None = None
    would_fetch: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """The one-line run summary of runbook §3, for the PR description (FR-01c)."""
        total = int(self.elapsed_s)
        clock = f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"
        line = (
            f"{self.source}: listed {self.listed:,} · stored {self.stored:,} · "
            f"filtered {self.filtered:,} · duplicate {self.duplicate:,} · failed {self.failed:,} · "
            f"skipped(already have) {self.skipped:,} · {clock}"
        )
        if self.dry_run:
            line += f" · dry run: would fetch {len(self.would_fetch):,}"
        if self.stopped:
            line += f" · STOPPED: {self.stopped}"
        return line


class Collector(ABC):
    """The resumable run loop shared by every source (runbook §5).

    A subclass sets ``source`` and implements ``iter_listed``.

    Args:
        cfg: Resolved config.
        session: The polite session to fetch through.
        manifest: The manifest to read and write.
        clock: Used for timestamps and run time. Defaults to the system clock.
    """

    source: ClassVar[str]

    def __init__(
        self,
        cfg: Config,
        session: PoliteSession,
        manifest: Manifest,
        clock: Clock | None = None,
    ) -> None:
        self.cfg = cfg
        self.session = session
        self.manifest = manifest
        self.clock = clock if clock is not None else SystemClock()
        self.raw_dir = paths.raw_dir(self.source, cfg)
        self._raw_root = raw_root(cfg)

    @abstractmethod
    def iter_listed(self) -> Iterator[ListedDoc]:
        """Yield every document the source's listing offers, fetching listing pages as needed."""

    def run(self, max_docs: int | None = None, dry_run: bool = False) -> RunStats:
        """Collect the source, resuming from the manifest.

        Args:
            max_docs: Stop after storing this many new documents.
            dry_run: Fetch listings only; report what would be downloaded and write nothing.

        Raises:
            SourceDisabled: The source has ``enabled: false``.
            SourceNotCleared: The source is enabled but its licence is unknown.
        """
        if not getattr(self.cfg.collect.sources, self.source).enabled:
            raise SourceDisabled(
                f"{self.source} has enabled: false in the config. Flip it only after "
                "docs/data/terms-of-use-audit.md clears the source."
            )
        load_registry(self.cfg)

        stats = RunStats(source=self.source, dry_run=dry_run)
        started = self.clock.monotonic()
        if not dry_run:
            shutil.rmtree(self.raw_dir / PARTIAL_DIRNAME, ignore_errors=True)
        try:
            for doc in self.iter_listed():
                stats.listed += 1
                self._handle(doc, stats, dry_run)
                if max_docs is not None and stats.stored >= max_docs:
                    break
        except StopCollection as exc:
            stats.stopped = str(exc)
        stats.elapsed_s = self.clock.monotonic() - started
        return stats

    # --- one listed document ---------------------------------------------------

    def _handle(self, doc: ListedDoc, stats: RunStats, dry_run: bool) -> None:
        if self._already_held(doc):
            stats.skipped += 1
            return
        if doc.product is None:
            stats.filtered += 1
            if not dry_run:
                self._log(doc, STATUS_FILTERED, f"not a health product: {doc.product_listed}")
            return
        if dry_run:
            stats.would_fetch.append(doc.url)
            return

        dest = self.raw_dir / f"{doc.doc_id}.{doc.extension}"
        try:
            partial = self.session.download_partial(doc.url, dest)
        except FetchFailed as exc:
            stats.failed += 1
            self._log(doc, STATUS_FAILED, exc.reason)
            return

        holder = self.manifest.doc_id_for_hash(partial.sha256)
        if holder is not None and holder != doc.doc_id:
            partial.discard()
            stats.duplicate += 1
            self._log(doc, STATUS_DUPLICATE, f"same bytes as {holder}")
            return

        # File first, manifest row second: a crash leaves a stray file, never a row without one.
        partial.commit()
        self.manifest.upsert(
            ManifestRow(
                doc_id=doc.doc_id,
                source=self.source,
                url=doc.url,
                decision_date=doc.decision_date.isoformat(),
                insurer=doc.insurer,
                product=doc.product,
                outcome_raw=doc.outcome_raw,
                office=doc.office,
                file_path=dest.relative_to(self._raw_root).as_posix(),
                file_sha256=partial.sha256,
                mime_type=partial.mime_type,
                fetched_at=self._timestamp(),
                collector_version=__version__,
            )
        )
        stats.stored += 1

    def _already_held(self, doc: ListedDoc) -> bool:
        """Whether this document needs no work: settled earlier and, if stored, intact on disk."""
        status = self.manifest.url_status(doc.url)
        if status in (STATUS_FILTERED, STATUS_DUPLICATE):
            return True
        if status != STATUS_STORED:
            return False
        row = self.manifest.get(doc.doc_id)
        if row is None:
            return False
        path = self._raw_root / row.file_path
        return path.is_file() and sha256_file(path) == row.file_sha256

    def _log(self, doc: ListedDoc, status: str, reason: str) -> None:
        self.manifest.log(CrawlEntry(doc.url, self.source, status, reason, self._timestamp()))

    def _timestamp(self) -> str:
        return self.clock.now().strftime("%Y-%m-%dT%H:%M:%SZ")
