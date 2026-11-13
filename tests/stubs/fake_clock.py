"""A clock for collector tests: ``sleep()`` advances time instantly (no real waiting)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


class FakeClock:
    """Monotonic fake clock implementing ``claimsense.collect.base.Clock``.

    Attributes:
        sleeps: Every duration passed to ``sleep``, in order.
    """

    def __init__(self, epoch: datetime | None = None) -> None:
        self._elapsed = 0.0
        self._epoch = epoch if epoch is not None else datetime(2026, 1, 1, tzinfo=UTC)
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        """Seconds since the clock was created."""
        return self._elapsed

    def sleep(self, seconds: float) -> None:
        """Advance time by ``seconds`` without waiting."""
        if seconds < 0:
            raise ValueError("cannot sleep for a negative time")
        self.sleeps.append(seconds)
        self._elapsed += seconds

    def advance(self, seconds: float) -> None:
        """Move time forward without recording a sleep (time passing between runs)."""
        self._elapsed += seconds

    def now(self) -> datetime:
        """The fake UTC time: a fixed epoch plus the elapsed seconds."""
        return self._epoch + timedelta(seconds=self._elapsed)
