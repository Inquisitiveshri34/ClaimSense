"""A fake HTTP transport that serves local files from a URL map (test-fixtures.md §4).

The map is a ``urlmap.yaml`` file (or a dict) from URL to one of:

* a file name, relative to the map's folder: served with status 200;
* a directive: ``"@404"``, ``"@403"``, ``"@503"``, ``"@429"``, ``"@timeout"``;
  ``"@429:30"`` / ``"@503:30"`` add ``Retry-After: 30``;
  ``"@truncated:<file>"`` serves the first half of a file under its full length;
* a list of the above: one entry per request to that URL, the last one repeating.

Any URL that is not in the map raises ``UnmappedURL``, so a collector that tries
to reach somewhere unexpected fails loudly. Every request is recorded with the
fake clock's time and its headers; that record is how politeness is asserted.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from claimsense.collect.transport import Response, TransportTimeout
from tests.stubs.fake_clock import FakeClock

CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".html": "text/html; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
}


class UnmappedURL(Exception):
    """A request was made for a URL that is not in the URL map."""


class SimulatedCrash(Exception):
    """The process 'died' mid-run (raised by ``FakeTransport.crash_after``)."""


@dataclass(frozen=True)
class RecordedRequest:
    """One request the fake transport received."""

    timestamp: float
    url: str
    headers: Mapping[str, str]


class FakeTransport:
    """Implements ``claimsense.collect.transport.Transport`` on local files.

    Attributes:
        requests: Every request received, in order.
        max_in_flight: The largest number of requests that were ever open at once.
    """

    def __init__(self, urlmap: Mapping[str, Any], root: Path, clock: FakeClock) -> None:
        self._map = {url: list(v) if isinstance(v, list) else [v] for url, v in urlmap.items()}
        self._served: dict[str, int] = {}
        self._root = Path(root)
        self._clock = clock
        self._crash_after: int | None = None
        self._crash_suffix = ""
        self._in_flight = 0
        self.max_in_flight = 0
        self.requests: list[RecordedRequest] = []

    @classmethod
    def from_urlmap(cls, path: Path, clock: FakeClock) -> FakeTransport:
        """Build a transport from a ``urlmap.yaml`` file; files are relative to its folder."""
        urlmap = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls(urlmap, Path(path).parent, clock)

    def crash_after(self, count: int, suffix: str = ".pdf") -> None:
        """Raise ``SimulatedCrash`` once ``count`` URLs ending in ``suffix`` were served."""
        self._crash_after = count
        self._crash_suffix = suffix

    def urls(self, suffix: str = "") -> list[str]:
        """The requested URLs, in order, optionally only those ending in ``suffix``."""
        return [r.url for r in self.requests if r.url.endswith(suffix)]

    def get(self, url: str, headers: Mapping[str, str], timeout: float) -> Response:
        """Serve ``url`` according to the map; see the module docstring."""
        self._in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self._in_flight)
        try:
            return self._serve(url, dict(headers))
        finally:
            self._in_flight -= 1

    def _serve(self, url: str, headers: dict[str, str]) -> Response:
        if self._crash_after is not None and url.endswith(self._crash_suffix):
            if len(self.urls(self._crash_suffix)) >= self._crash_after:
                self._crash_after = None
                raise SimulatedCrash(f"simulated crash before {url}")
        self.requests.append(RecordedRequest(self._clock.monotonic(), url, headers))
        if url not in self._map:
            raise UnmappedURL(url)

        entries = self._map[url]
        index = min(self._served.get(url, 0), len(entries) - 1)
        self._served[url] = self._served.get(url, 0) + 1
        entry = str(entries[index])
        if not entry.startswith("@"):
            return self._file_response(url, entry)

        name, _, argument = entry[1:].partition(":")
        if name == "timeout":
            raise TransportTimeout(f"simulated timeout for {url}")
        if name == "truncated":
            body = (self._root / argument).read_bytes()
            return Response(
                url=url,
                status=200,
                headers={"content-type": _content_type(argument)},
                content=body[: len(body) // 2],
                expected_length=len(body),
            )
        if name.isdigit():
            response_headers = {"retry-after": argument} if argument else {}
            return Response(url=url, status=int(name), headers=response_headers)
        raise ValueError(f"unknown directive {entry!r} for {url}")

    def _file_response(self, url: str, name: str) -> Response:
        body = (self._root / name).read_bytes()
        return Response(
            url=url,
            status=200,
            headers={"content-type": _content_type(name)},
            content=body,
            expected_length=len(body),
        )


def _content_type(name: str) -> str:
    return CONTENT_TYPES.get(Path(name).suffix.lower(), "application/octet-stream")
