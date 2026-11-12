"""Shared names used by every stage: outcome labels, sources and their countries.

The record dataclasses and the ``RejectionReason`` enum of
docs/architecture/data-schema.md are added in PR 4.
"""

from __future__ import annotations

# The three outcome classes, in this order everywhere (model outputs,
# probability columns, reports).
LABELS: tuple[str, ...] = ("upheld", "partially_upheld", "rejected")

# Ombudsman sources: CIOINS (India), FOS (UK), FSPO (Ireland).
SOURCES: tuple[str, ...] = ("cioins", "fos", "fspo")

# ISO 3166-1 alpha-2 country of each source.
COUNTRY_OF_SOURCE: dict[str, str] = {"cioins": "IN", "fos": "GB", "fspo": "IE"}
