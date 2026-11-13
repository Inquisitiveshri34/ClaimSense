"""How a collector reaches a site: one ``get`` call, behind a protocol.

``PoliteSession`` (``claimsense.collect.base``) owns every rule about when a
request may be made. A transport only performs the request it is given, so
tests swap in a fake transport and never touch the network.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol


class TransportError(Exception):
    """The request did not produce a response (connection failed, reset, incomplete)."""


class TransportTimeout(TransportError):
    """The request did not finish within the timeout."""


@dataclass(frozen=True)
class Response:
    """One HTTP response, fully read.

    Attributes:
        url: Final URL after redirects.
        status: HTTP status code.
        headers: Response headers with lower-case names.
        content: The decoded body.
        expected_length: Number of body bytes the server announced, when it is
            comparable with ``len(content)``; ``None`` otherwise. A mismatch
            means the body was cut short.
    """

    url: str
    status: int
    headers: Mapping[str, str] = field(default_factory=dict)
    content: bytes = b""
    expected_length: int | None = None

    @property
    def truncated(self) -> bool:
        """Whether fewer bytes arrived than the server announced."""
        return self.expected_length is not None and len(self.content) != self.expected_length


class Transport(Protocol):
    """Performs one GET request. Implementations hold at most one connection."""

    def get(self, url: str, headers: Mapping[str, str], timeout: float) -> Response:
        """Fetch ``url`` and return the response.

        Raises:
            TransportTimeout: No complete response within ``timeout`` seconds.
            TransportError: Any other failure to obtain a response.
        """
        ...


class RequestsTransport:
    """The real transport: one ``requests`` session with a single pooled connection."""

    def __init__(self) -> None:
        import requests
        from requests.adapters import HTTPAdapter

        self._requests = requests
        self._session = requests.Session()
        # One connection, and no retries here: PoliteSession decides when to retry.
        adapter = HTTPAdapter(pool_connections=1, pool_maxsize=1, max_retries=0)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def get(self, url: str, headers: Mapping[str, str], timeout: float) -> Response:
        """Fetch ``url`` with ``requests``; see ``Transport.get``."""
        try:
            raw = self._session.get(url, headers=dict(headers), timeout=timeout)
        except self._requests.Timeout as exc:
            raise TransportTimeout(str(exc)) from exc
        except self._requests.RequestException as exc:
            raise TransportError(str(exc)) from exc

        response_headers = {name.lower(): value for name, value in raw.headers.items()}
        expected_length: int | None = None
        # Content-Length counts encoded bytes, so it is only comparable with the
        # decoded body when the response is not compressed.
        length = response_headers.get("content-length", "")
        if length.isdigit() and "content-encoding" not in response_headers:
            expected_length = int(length)
        return Response(
            url=raw.url,
            status=raw.status_code,
            headers=response_headers,
            content=raw.content,
            expected_length=expected_length,
        )

    def close(self) -> None:
        """Close the underlying connection."""
        self._session.close()
