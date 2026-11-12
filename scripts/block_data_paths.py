"""Pre-commit hook: refuse to commit data, original PDFs or secrets files.

Local mirror of the CI ``guard`` job (docs/operations/ci-cd.md §3.4 and §7,
privacy control P-R5). pre-commit passes the staged paths as arguments; the
hook exits non-zero and names each offending path.

Blocked:
* anything under ``data/`` except ``data/.gitkeep`` and ``data/README.md``;
* any ``_pii_quarantine/`` directory;
* ``*.pdf`` outside ``tests/fixtures/``;
* ``.env``, ``kaggle.json`` and ``*.pem`` anywhere.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import PurePosixPath

ALLOWED_DATA_PATHS = frozenset({"data/.gitkeep", "data/README.md"})
PDF_ALLOWED_ROOT = ("tests", "fixtures")
SECRET_FILENAMES = frozenset({".env", "kaggle.json"})


def violation(path: str) -> str | None:
    """Return why ``path`` must not be committed, or ``None`` if it is allowed."""
    posix = PurePosixPath(path.replace("\\", "/"))
    parts = posix.parts
    name = posix.name.lower()

    if parts and parts[0] == "data" and posix.as_posix() not in ALLOWED_DATA_PATHS:
        return "path under data/; data is never committed"
    if "_pii_quarantine" in parts:
        return "PII quarantine path"
    if name.endswith(".pdf") and parts[:2] != PDF_ALLOWED_ROOT:
        return "PDF outside tests/fixtures/"
    if name in SECRET_FILENAMES or name.endswith(".pem"):
        return "secrets file"
    return None


def main(argv: Sequence[str] | None = None) -> int:
    """Check every path given on the command line; return 1 if any is blocked."""
    paths = list(sys.argv[1:] if argv is None else argv)
    blocked = [(path, reason) for path in paths if (reason := violation(path)) is not None]
    for path, reason in blocked:
        print(f"BLOCKED  {path}  ({reason})", file=sys.stderr)
    if blocked:
        print("Unstage these files (git restore --staged <path>).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
