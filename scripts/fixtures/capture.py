"""Capture one page from a source for use as a test fixture (test-fixtures.md §2, §8).

One polite request (after reading the site's robots.txt), with the project's
identified User-Agent. Records the date, size and SHA-256 and prints a starting
entry for ``tests/fixtures/FIXTURES.yaml``::

    CLAIMSENSE_CONFIG=configs/local.yaml \\
      uv run python scripts/fixtures/capture.py --source fspo --url <URL> \\
      --out tests/fixtures_local/fspo/list_p1.html

Rules this script enforces:

* ``collect.contact_email`` must be set (use a local override file).
* A page from a source whose derived text may not be redistributed is saved
  only outside ``tests/fixtures/``. Redact it with ``redact_html.py``, review
  it, and add the redacted copy to the repo, never the capture.

Not run in tests.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from claimsense import config
from claimsense.collect.base import CollectionError, PoliteSession, SystemClock
from claimsense.collect.sources import FIXTURE_POLICY_SAVED_ALLOWED, load_registry
from claimsense.schema import SOURCES

COMMITTED_FIXTURES = config.repo_root() / "tests" / "fixtures"


def main() -> int:
    """Capture one page and print its fixture-manifest entry."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", required=True, choices=SOURCES)
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    cfg = config.load()
    registry = load_registry(cfg)
    out = args.out.resolve()
    policy = registry.fixture_policy(args.source)
    if policy != FIXTURE_POLICY_SAVED_ALLOWED and out.is_relative_to(COMMITTED_FIXTURES):
        print(
            f"{args.source} fixtures are {policy}: save the capture under tests/fixtures_local/, "
            "redact it with scripts/fixtures/redact_html.py, and commit only the redacted copy.",
            file=sys.stderr,
        )
        return 1
    if not args.url.startswith(registry[args.source].base_url):
        print(f"{args.url} is not on {registry[args.source].base_url}", file=sys.stderr)
        return 1

    clock = SystemClock()
    try:
        session = PoliteSession(cfg, clock=clock)
        response = session.get(args.url)
    except CollectionError as exc:
        print(f"capture: {exc}", file=sys.stderr)
        return 1

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(response.content)
    digest = hashlib.sha256(response.content).hexdigest()
    print(f"saved {out} ({len(response.content):,} bytes) with {session.requests_made} requests")
    print()
    print("# FIXTURES.yaml entry to start from (fix path and kind after redaction):")
    print(f"- path: {out.name}")
    print(f"  kind: {'saved' if policy == FIXTURE_POLICY_SAVED_ALLOWED else 'saved-redacted'}")
    print(f"  source: {args.source}")
    print(f"  captured: {clock.now().date().isoformat()}")
    print(f'  sha256: "{digest}"')
    print("  contains_personal_data: false")
    print("  used_by: []")
    return 0


if __name__ == "__main__":
    sys.exit(main())
