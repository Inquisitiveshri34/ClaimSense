"""Turn a saved listing page into a committable, redacted fixture (test-fixtures.md §2).

A saved page from a source that is not cleared for redistribution (CIOINS, FOS)
can show real names, case titles and reference numbers. This helper keeps the
page's structure (tags, classes, pagination markup) and replaces that content
with fictional values. It is a helper, not a guarantee: **review the output by
hand** and record your initials in ``tests/fixtures/FIXTURES.yaml``.

Two commands::

    # 1. Look at the structure without showing any page text (safe to paste anywhere)
    uv run python scripts/fixtures/redact_html.py outline saved.html
    uv run python scripts/fixtures/redact_html.py outline saved.html --show-text th --show-href

    # 2. Write the redacted copy
    uv run python scripts/fixtures/redact_html.py redact saved.html out.html --rules rules.yaml

``rules.yaml`` (every key optional; values are CSS selectors)::

    drop: ["script", "style", "noscript", "input[type=hidden]"]   # removed entirely
    person: ["td.complainant"]        # text -> "Demo Person 001", same input -> same output
    reference: ["td.awardno"]         # digits renumbered consistently, other characters kept
    text:                             # text -> a fixed replacement
      "td.subject": "Synthetic case title"
    keep_first:                       # keep only the first N matches, remove the rest
      "table.awards tbody tr": 12
    href_reference: ["td.awardno a"]  # digits in the link's file name renumbered the same way
    blank_attributes: ["title", "alt"]  # these attributes are emptied everywhere

HTML comments are always removed. Not run in tests.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from bs4 import BeautifulSoup, Comment, NavigableString, Tag

STRUCTURAL_ATTRIBUTES = ("id", "class", "type", "name", "role", "colspan", "rowspan", "method")
DEFAULT_DROP = ("script", "style", "noscript", "input[type=hidden]")
PERSON_TEMPLATE = "Demo Person {n:03d}"


# --- outline ---------------------------------------------------------------------


def _mask_href(href: str) -> str:
    """Show the shape of a link (letters -> a, digits -> 9) but not its content."""
    return re.sub(r"[0-9]", "9", re.sub(r"[A-Za-z]", "a", href))


def _signature(tag: Tag, shown: set[int], show_href: bool) -> str:
    parts = [tag.name]
    for name in STRUCTURAL_ATTRIBUTES:
        if tag.has_attr(name):
            value = tag[name]
            parts.append(f'{name}="{" ".join(value) if isinstance(value, list) else value}"')
    for name in ("href", "src", "action"):
        if tag.has_attr(name):
            value = str(tag[name])
            parts.append(f'{name}="{value if show_href else _mask_href(value)}"')
    text = " ".join(tag.get_text(" ", strip=True).split())
    own_text = "".join(str(c) for c in tag.children if isinstance(c, NavigableString)).strip()
    if own_text:
        if id(tag) in shown:
            parts.append(f"text={text!r}")
        else:
            parts.append(f"text=<{len(text)} chars, {len(text.split())} words>")
    return " ".join(parts)


def _outline_lines(tag: Tag, depth: int, shown: set[int], show_href: bool) -> list[str]:
    lines = ["  " * depth + _signature(tag, shown, show_href)]
    children = [child for child in tag.children if isinstance(child, Tag)]
    blocks = [_outline_lines(child, depth + 1, shown, show_href) for child in children]
    # Collapse runs of siblings that look the same, so a 200-row table prints once.
    index = 0
    while index < len(blocks):
        run = 1
        while index + run < len(blocks) and _shape(blocks[index + run]) == _shape(blocks[index]):
            run += 1
        lines.extend(blocks[index])
        if run > 1:
            lines.append("  " * (depth + 1) + f"... x{run} siblings with this shape")
        index += run
    return lines


def _shape(block: list[str]) -> list[str]:
    """A block with everything that varies between similar rows removed."""
    return [
        re.sub(r'(text|href|src|action)=("[^"]*"|<[^>]*>|\'[^\']*\')', r"\1=…", line)
        for line in block
    ]  # noqa: E501


def outline(html: str, show_text: list[str], show_href: bool) -> str:
    """Return the page's structure. Text is masked unless its element matches ``show_text``."""
    soup = BeautifulSoup(html, "lxml")
    for selector in DEFAULT_DROP:
        for tag in soup.select(selector):
            tag.replace_with(soup.new_string(""))
    shown = {id(tag) for selector in show_text for tag in soup.select(selector)}
    root = soup.body or soup
    return "\n".join(_outline_lines(root, 0, shown, show_href))


# --- redact ----------------------------------------------------------------------


class _Renumber:
    """Maps each distinct value to a stable replacement: the same input gives the same output."""

    def __init__(self, make: Callable[[int, str], str]) -> None:
        self._make = make
        self._seen: dict[str, str] = {}

    def __call__(self, value: str) -> str:
        if value not in self._seen:
            self._seen[value] = self._make(len(self._seen) + 1, value)
        return self._seen[value]

    def __len__(self) -> int:
        return len(self._seen)


def _set_text(tag: Tag, text: str) -> None:
    """Replace the text of ``tag`` while keeping its child elements' markup where possible."""
    strings = [s for s in tag.find_all(string=True) if not isinstance(s, Comment) and s.strip()]
    if not strings:
        return
    strings[0].replace_with(text)
    for extra in strings[1:]:
        extra.replace_with("")


def redact(html: str, rules: dict[str, Any]) -> tuple[str, dict[str, int]]:
    """Apply ``rules`` to ``html``; return the redacted page and a count per rule."""
    soup = BeautifulSoup(html, "lxml")
    counts: dict[str, int] = {}

    def bump(rule: str, by: int = 1) -> None:
        counts[rule] = counts.get(rule, 0) + by

    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()
        bump("comments")
    for selector in rules.get("drop", DEFAULT_DROP):
        for tag in soup.select(selector):
            tag.decompose()
            bump("drop")
    for selector, limit in (rules.get("keep_first") or {}).items():
        for tag in soup.select(selector)[int(limit) :]:
            tag.decompose()
            bump("keep_first")

    person = _Renumber(lambda n, _: PERSON_TEMPLATE.format(n=n))
    number = _Renumber(lambda n, original: str(n).zfill(len(original)))

    def renumber(text: str) -> str:
        return re.sub(r"\d+", lambda match: number(match.group()), text)

    for selector in rules.get("person", []):
        for tag in soup.select(selector):
            original = " ".join(tag.get_text(" ", strip=True).split())
            if original:
                _set_text(tag, person(original))
                bump("person")
    for selector in rules.get("reference", []):
        for tag in soup.select(selector):
            for string in tag.find_all(string=True):
                if string.strip():
                    string.replace_with(renumber(str(string)))
            bump("reference")
    for selector, replacement in (rules.get("text") or {}).items():
        for tag in soup.select(selector):
            _set_text(tag, str(replacement))
            bump("text")
    for selector in rules.get("href_reference", []):
        for tag in soup.select(selector):
            if tag.has_attr("href"):
                head, slash, name = str(tag["href"]).rpartition("/")
                tag["href"] = head + slash + renumber(name)
                bump("href_reference")
    for name in rules.get("blank_attributes", []):
        for tag in soup.find_all(attrs={name: True}):
            tag[name] = ""
            bump("blank_attributes")

    return str(soup), counts


def main() -> int:
    """Run the ``outline`` or ``redact`` command."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    show = commands.add_parser("outline", help="print the structure with all text masked")
    show.add_argument("page", type=Path)
    show.add_argument(
        "--show-text", action="append", default=[], metavar="CSS", help="reveal text here"
    )
    show.add_argument("--show-href", action="store_true", help="print link targets unmasked")
    write = commands.add_parser("redact", help="write a redacted copy")
    write.add_argument("page", type=Path)
    write.add_argument("out", type=Path)
    write.add_argument("--rules", type=Path, required=True)
    args = parser.parse_args()

    html = args.page.read_text(encoding="utf-8", errors="replace")
    if args.command == "outline":
        print(outline(html, args.show_text, args.show_href))
        return 0

    rules = yaml.safe_load(args.rules.read_text(encoding="utf-8")) or {}
    redacted, counts = redact(html, rules)
    args.out.write_text(redacted, encoding="utf-8")
    for rule, count in sorted(counts.items()):
        print(f"{rule:<18} {count:>6}")
    print(f"wrote {args.out} ({len(redacted.encode('utf-8')):,} bytes)")
    print("Now read the whole file yourself. Anything real left in it must go before it is added.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
