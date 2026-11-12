"""Shared names (data-schema.md; 00-CONVENTIONS.md §5): label order, sources, countries."""

from __future__ import annotations

from claimsense.schema import COUNTRY_OF_SOURCE, LABELS, SOURCES


def test_labels_order_and_contents() -> None:
    # This order is a cross-PR contract: model outputs and probability columns follow it.
    assert LABELS == ("upheld", "partially_upheld", "rejected")


def test_sources() -> None:
    assert SOURCES == ("cioins", "fos", "fspo")
    assert len(set(SOURCES)) == len(SOURCES)


def test_every_source_has_a_country() -> None:
    assert set(COUNTRY_OF_SOURCE) == set(SOURCES)
    assert COUNTRY_OF_SOURCE == {"cioins": "IN", "fos": "GB", "fspo": "IE"}
