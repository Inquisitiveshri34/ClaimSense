"""Collector command line (docs/data/collection-runbook.md §3).

::

    python -m claimsense.collect run --source cioins [--max-docs N] [--dry-run]
    python -m claimsense.collect verify     # re-hash every stored file; exit 1 on any problem
    python -m claimsense.collect report     # counts by status, year and office
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import TextIO

from claimsense import config
from claimsense.collect.base import Clock, CollectionError, Collector, PoliteSession
from claimsense.collect.cioins import CioinsCollector
from claimsense.collect.manifest import Manifest, manifest_path, raw_root
from claimsense.collect.sources import SourceNotCleared
from claimsense.collect.transport import Transport

# One collector class per source; PR 4 adds FOS and FSPO.
COLLECTORS: dict[str, type[Collector]] = {CioinsCollector.source: CioinsCollector}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m claimsense.collect",
        description="Collect ombudsman decisions politely and resumably.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="collect one source (resumes automatically)")
    run.add_argument("--source", required=True, choices=sorted(COLLECTORS))
    run.add_argument("--max-docs", type=int, default=None, help="stop after N new documents")
    run.add_argument(
        "--dry-run", action="store_true", help="list what would be fetched; write nothing"
    )
    commands.add_parser("verify", help="compare the manifest with the files on disk")
    commands.add_parser("report", help="print counts by status, year and office")
    return parser


def _run(
    args: argparse.Namespace,
    cfg: config.Config,
    transport: Transport | None,
    clock: Clock | None,
    out: TextIO,
) -> int:
    try:
        session = PoliteSession(cfg, transport=transport, clock=clock, dry_run=args.dry_run)
        with Manifest(manifest_path(cfg)) as manifest:
            collector = COLLECTORS[args.source](cfg, session, manifest, clock=clock)
            stats = collector.run(max_docs=args.max_docs, dry_run=args.dry_run)
    except (CollectionError, SourceNotCleared) as exc:
        print(f"collect: {exc}", file=sys.stderr)
        return 1
    for url in stats.would_fetch:
        print(f"would fetch {url}", file=out)
    print(stats.summary(), file=out)
    return 1 if stats.stopped else 0


def _verify(cfg: config.Config, out: TextIO) -> int:
    with Manifest(manifest_path(cfg)) as manifest:
        problems = manifest.verify(raw_root(cfg))
        checked = len(manifest.rows())
    for problem in problems:
        owner = f" ({problem.doc_id})" if problem.doc_id else ""
        print(f"{problem.kind}: {problem.path}{owner}", file=out)
    print(f"verify: {checked} rows checked · {len(problems)} problems", file=out)
    return 1 if problems else 0


def _report(cfg: config.Config, out: TextIO) -> int:
    with Manifest(manifest_path(cfg)) as manifest:
        report = manifest.report()
    for title, counts in report.items():
        print(f"by {title}:", file=out)
        if not counts:
            print("  (none)", file=out)
        for key, count in counts.items():
            print(f"  {key:<24} {count:>7,}", file=out)
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    transport: Transport | None = None,
    clock: Clock | None = None,
    out: TextIO | None = None,
) -> int:
    """Run a collector command and return its exit code.

    Args:
        argv: Command-line arguments; defaults to ``sys.argv[1:]``.
        transport: Replaces the real HTTP transport (tests).
        clock: Replaces the system clock (tests).
        out: Where results are printed; defaults to standard output.
    """
    args = _build_parser().parse_args(argv)
    out = out if out is not None else sys.stdout
    cfg = config.load()
    if args.command == "run":
        return _run(args, cfg, transport, clock, out)
    if args.command == "verify":
        return _verify(cfg, out)
    return _report(cfg, out)


if __name__ == "__main__":
    sys.exit(main())
