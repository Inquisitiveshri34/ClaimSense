"""Placeholder (NFR-10): proves pytest collects and runs, and that the package is installed."""

import claimsense


def test_pytest_runs() -> None:
    assert claimsense.__version__
