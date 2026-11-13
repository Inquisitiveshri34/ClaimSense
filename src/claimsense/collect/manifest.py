"""The download manifest: one SQLite file shared by all sources (FR-02, FR-03).

Two tables, exactly as ``docs/architecture/data-schema.md`` §2 defines them:

* ``manifest``: one row per stored document.
* ``crawl_log``: one row per document URL seen, with what happened to it
  (``stored``, ``filtered``, ``failed``, ``duplicate``), so a re-run knows what
  it has already dealt with.

The file stays on the local machine: URLs link back to named individuals' decisions.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterator
from dataclasses import astuple, dataclass, fields
from pathlib import Path
from types import TracebackType

from claimsense import paths
from claimsense.config import Config

MANIFEST_FILENAME = "manifest.sqlite"
PARTIAL_DIRNAME = ".partial"

STATUS_STORED = "stored"
STATUS_FILTERED = "filtered"
STATUS_FAILED = "failed"
STATUS_DUPLICATE = "duplicate"
STATUSES = (STATUS_STORED, STATUS_FILTERED, STATUS_FAILED, STATUS_DUPLICATE)
# A URL with one of these statuses has been dealt with; a failed URL is retried.
SETTLED_STATUSES = (STATUS_STORED, STATUS_FILTERED, STATUS_DUPLICATE)

# docs/architecture/data-schema.md §2, unchanged.
DDL = """
CREATE TABLE IF NOT EXISTS manifest (
    doc_id            TEXT PRIMARY KEY,
    source            TEXT NOT NULL CHECK (source IN ('cioins','fos','fspo')),
    url               TEXT NOT NULL,
    decision_date     TEXT NOT NULL CHECK (decision_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    insurer           TEXT NOT NULL,
    product           TEXT NOT NULL CHECK (product IN
                        ('individual_mediclaim','group_mediclaim','overseas_mediclaim','private_health')),
    outcome_raw       TEXT NOT NULL,
    office            TEXT,
    file_path         TEXT NOT NULL,
    file_sha256       TEXT NOT NULL UNIQUE CHECK (length(file_sha256) = 64),
    mime_type         TEXT NOT NULL,
    fetched_at        TEXT NOT NULL,
    collector_version TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_manifest_source_date ON manifest (source, decision_date);

-- Pages visited but not stored (filtered out, failed, skipped), so re-runs know what was seen.
CREATE TABLE IF NOT EXISTS crawl_log (
    url         TEXT PRIMARY KEY,
    source      TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('stored','filtered','failed','duplicate')),
    reason      TEXT,
    seen_at     TEXT NOT NULL
);
"""  # noqa: E501


@dataclass(frozen=True)
class ManifestRow:
    """One stored document; fields and order follow the ``manifest`` table.

    ``file_path`` is relative to the raw data directory. ``outcome_raw`` is the
    source's own outcome wording when the listing gives one, else an empty string.
    """

    doc_id: str
    source: str
    url: str
    decision_date: str
    insurer: str
    product: str
    outcome_raw: str
    office: str | None
    file_path: str
    file_sha256: str
    mime_type: str
    fetched_at: str
    collector_version: str


@dataclass(frozen=True)
class CrawlEntry:
    """One document URL the collector has seen; fields follow the ``crawl_log`` table."""

    url: str
    source: str
    status: str
    reason: str | None
    seen_at: str


@dataclass(frozen=True)
class Problem:
    """One inconsistency between the manifest and the files on disk.

    ``kind`` is ``missing`` (row without file), ``hash_mismatch`` (file changed),
    ``orphan_file`` (file without row) or ``partial`` (leftover partial download).
    """

    kind: str
    path: str
    doc_id: str | None = None


_MANIFEST_COLUMNS = tuple(f.name for f in fields(ManifestRow))
_CRAWL_COLUMNS = tuple(f.name for f in fields(CrawlEntry))


def manifest_path(cfg: Config | None = None) -> Path:
    """Return ``<data>/manifests/manifest.sqlite``."""
    return paths.data_dir(cfg) / "manifests" / MANIFEST_FILENAME


def raw_root(cfg: Config | None = None) -> Path:
    """Return ``<data>/raw``, the directory ``ManifestRow.file_path`` is relative to."""
    return paths.data_dir(cfg) / "raw"


def sha256_file(path: Path) -> str:
    """Return the SHA-256 of a file as 64 hex characters."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Manifest:
    """The manifest database. Creates the file and both tables if they do not exist."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path)
        self._db.executescript(DDL)
        self._db.commit()

    def __enter__(self) -> Manifest:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Close the database."""
        self._db.close()

    # --- writes ---------------------------------------------------------------

    def upsert(self, row: ManifestRow) -> None:
        """Insert a stored document, or update the one with the same ``doc_id``.

        The row and its ``stored`` crawl entry are written in one transaction.

        Raises:
            sqlite3.IntegrityError: A constraint fails, for example another document
                already has the same ``file_sha256``.
        """
        placeholders = ", ".join("?" for _ in _MANIFEST_COLUMNS)
        updates = ", ".join(f"{c} = excluded.{c}" for c in _MANIFEST_COLUMNS if c != "doc_id")
        with self._db:
            self._db.execute(
                f"INSERT INTO manifest ({', '.join(_MANIFEST_COLUMNS)}) VALUES ({placeholders}) "
                f"ON CONFLICT(doc_id) DO UPDATE SET {updates}",
                astuple(row),
            )
            self._log(CrawlEntry(row.url, row.source, STATUS_STORED, None, row.fetched_at))

    def log(self, entry: CrawlEntry) -> None:
        """Record what happened to a URL that was not stored (filtered, failed, duplicate)."""
        with self._db:
            self._log(entry)

    def _log(self, entry: CrawlEntry) -> None:
        placeholders = ", ".join("?" for _ in _CRAWL_COLUMNS)
        self._db.execute(
            f"INSERT OR REPLACE INTO crawl_log ({', '.join(_CRAWL_COLUMNS)}) "
            f"VALUES ({placeholders})",
            astuple(entry),
        )

    # --- reads ----------------------------------------------------------------

    def get(self, doc_id: str) -> ManifestRow | None:
        """Return the stored document with this ``doc_id``, if any."""
        found = self._db.execute(
            f"SELECT {', '.join(_MANIFEST_COLUMNS)} FROM manifest WHERE doc_id = ?", (doc_id,)
        ).fetchone()
        return ManifestRow(*found) if found else None

    def url_status(self, url: str) -> str | None:
        """Return the crawl status of a URL, or ``None`` if it has never been seen."""
        found = self._db.execute("SELECT status FROM crawl_log WHERE url = ?", (url,)).fetchone()
        return found[0] if found else None

    def has_url(self, url: str) -> bool:
        """Whether this URL has been dealt with (stored, filtered or duplicate)."""
        return self.url_status(url) in SETTLED_STATUSES

    def doc_id_for_hash(self, sha256: str) -> str | None:
        """Return the ``doc_id`` of the stored document with these bytes, if any."""
        found = self._db.execute(
            "SELECT doc_id FROM manifest WHERE file_sha256 = ?", (sha256,)
        ).fetchone()
        return found[0] if found else None

    def has_hash(self, sha256: str) -> bool:
        """Whether a stored document already has these bytes."""
        return self.doc_id_for_hash(sha256) is not None

    def rows(self, source: str | None = None) -> list[ManifestRow]:
        """Return the stored documents, ordered by ``doc_id``; optionally one source only."""
        query = f"SELECT {', '.join(_MANIFEST_COLUMNS)} FROM manifest"
        params: tuple[str, ...] = ()
        if source is not None:
            query += " WHERE source = ?"
            params = (source,)
        return [ManifestRow(*r) for r in self._db.execute(query + " ORDER BY doc_id", params)]

    def crawl_entries(self, source: str | None = None) -> list[CrawlEntry]:
        """Return every URL seen, ordered by URL; optionally one source only."""
        query = f"SELECT {', '.join(_CRAWL_COLUMNS)} FROM crawl_log"
        params: tuple[str, ...] = ()
        if source is not None:
            query += " WHERE source = ?"
            params = (source,)
        return [CrawlEntry(*r) for r in self._db.execute(query + " ORDER BY url", params)]

    def gaps(self, source: str | None = None) -> list[CrawlEntry]:
        """Return the listed documents that were not obtained (status ``failed``)."""
        return [e for e in self.crawl_entries(source) if e.status == STATUS_FAILED]

    # --- checks ---------------------------------------------------------------

    def verify(self, raw_dir: Path) -> list[Problem]:
        """Compare the manifest with the files under ``raw_dir`` (runbook §5).

        Recomputes every stored file's hash and reports rows without files,
        changed files, files without rows and leftover partial downloads.
        """
        problems: list[Problem] = []
        expected: set[Path] = set()
        for row in self.rows():
            path = raw_dir / row.file_path
            expected.add(path)
            if not path.is_file():
                problems.append(Problem("missing", row.file_path, row.doc_id))
            elif sha256_file(path) != row.file_sha256:
                problems.append(Problem("hash_mismatch", row.file_path, row.doc_id))
        for path in _files_under(raw_dir):
            relative = path.relative_to(raw_dir).as_posix()
            if PARTIAL_DIRNAME in path.relative_to(raw_dir).parts:
                problems.append(Problem("partial", relative))
            elif path not in expected:
                problems.append(Problem("orphan_file", relative))
        return problems

    def report(self) -> dict[str, dict[str, int]]:
        """Return counts by crawl status, by decision year and by office (``report`` command)."""
        return {
            "status": self._counts("SELECT status, COUNT(*) FROM crawl_log GROUP BY status"),
            "year": self._counts(
                "SELECT substr(decision_date, 1, 4), COUNT(*) FROM manifest GROUP BY 1"
            ),
            "office": self._counts(
                "SELECT COALESCE(office, '(none)'), COUNT(*) FROM manifest GROUP BY 1"
            ),
        }

    def _counts(self, query: str) -> dict[str, int]:
        return {str(key): int(count) for key, count in sorted(self._db.execute(query))}


def _files_under(directory: Path) -> Iterator[Path]:
    """Yield every file below ``directory`` in a stable order."""
    if not directory.is_dir():
        return
    yield from sorted(path for path in directory.rglob("*") if path.is_file())
