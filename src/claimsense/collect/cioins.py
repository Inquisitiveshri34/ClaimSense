"""CIOINS collector: health awards of the Council for Insurance Ombudsmen (India).

Flow (docs/data/collection-runbook.md §6.1): the health archive lists months;
each month page lists awards per ombudsman office; each award is one PDF.

.. warning:: **The listing layout below is an assumption, not a verified fact.**

   CIOINS is not cleared for collection (``docs/data/terms-of-use-audit.md``),
   and its archive entry point was not found when checked on 2026-11-13
   (``DATA_SOURCES.md``). No real page was available when this module was
   written, so ``parse_archive_index`` and ``parse_month_page`` read the layout
   of the *synthetic* pages in ``tests/fixtures/collect/cioins/`` and of the
   e2e world. Before any live run: capture the real pages
   (``scripts/fixtures/capture.py``), add them as redacted ``_v2`` fixtures and
   change the two parse functions until both layouts pass (test-fixtures.md §8).
   Nothing outside those two functions depends on the layout.
"""

from __future__ import annotations

import calendar
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from claimsense.collect.base import Collector, FetchFailed, ListedDoc, StopCollection
from claimsense.collect.transport import Response

SOURCE = "cioins"

# --- assumed layout: the only layout-specific part of this module --------------
MONTH_LINK = "a.month-link"  # archive index: one link per month, text "May 2023"
OFFICE_BLOCK = "div.office"  # month page: one block per ombudsman office
OFFICE_NAME = ".office-name"
AWARD_ROW = "table.awards tbody tr"
AWARD_NO = "td.award-no"
AWARD_DATE = "td.award-date"
INSURER = "td.insurer"
POLICY_TYPE = "td.policy-type"
AWARD_PDF = "a.award-pdf"
DATE_FORMATS = ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d")
# --------------------------------------------------------------------------------

_MONTH_NUMBER = {name.lower(): number for number, name in enumerate(calendar.month_name) if name}
_MONTH_TEXT = re.compile(r"([A-Za-z]+)\s+(\d{4})")


class ListingChanged(StopCollection):
    """A listing page does not have the expected structure (risk R14); the run stops."""


@dataclass(frozen=True)
class MonthLink:
    """One month in the archive index."""

    year: int
    month: int
    url: str


@dataclass(frozen=True)
class AwardLink:
    """One award row on a month page."""

    office: str
    award_no: str
    award_date: date
    insurer: str
    policy_type: str
    url: str


def _slug(text: str) -> str:
    """Lower-case ``text`` with every run of other characters turned into one hyphen."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _text(row: Tag, selector: str, what: str, page_url: str) -> str:
    cell = row.select_one(selector)
    value = " ".join(cell.get_text(" ", strip=True).split()) if cell is not None else ""
    if not value:
        raise ListingChanged(f"award row without {what} on {page_url}")
    return value


def _parse_date(text: str, page_url: str) -> date:
    for pattern in DATE_FORMATS:
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise ListingChanged(f"unreadable award date {text!r} on {page_url}")


def parse_archive_index(html: bytes | str, page_url: str) -> list[MonthLink]:
    """Return the months the archive index links to, in page order.

    Raises:
        ListingChanged: A month link's text is not ``<month name> <year>``.
    """
    soup = BeautifulSoup(html, "lxml")
    months: list[MonthLink] = []
    for link in soup.select(MONTH_LINK):
        label = link.get_text(" ", strip=True)
        match = _MONTH_TEXT.search(label)
        number = _MONTH_NUMBER.get(match.group(1).lower()) if match else None
        href = link.get("href")
        if match is None or number is None or not href:
            raise ListingChanged(f"unreadable month link {label!r} on {page_url}")
        months.append(MonthLink(int(match.group(2)), number, urljoin(page_url, str(href))))
    return months


def parse_month_page(html: bytes | str, page_url: str) -> list[AwardLink]:
    """Return the awards a month page lists, office by office. An empty month gives ``[]``.

    Raises:
        ListingChanged: An award row lacks its number, date, insurer, policy type or link.
    """
    soup = BeautifulSoup(html, "lxml")
    awards: list[AwardLink] = []
    for block in soup.select(OFFICE_BLOCK):
        office = _text(block, OFFICE_NAME, "an office name", page_url)
        for row in block.select(AWARD_ROW):
            link = row.select_one(AWARD_PDF)
            if link is None or not link.get("href"):
                raise ListingChanged(f"award row without a PDF link on {page_url}")
            awards.append(
                AwardLink(
                    office=office,
                    award_no=_text(row, AWARD_NO, "an award number", page_url),
                    award_date=_parse_date(_text(row, AWARD_DATE, "a date", page_url), page_url),
                    insurer=_text(row, INSURER, "an insurer", page_url),
                    policy_type=_text(row, POLICY_TYPE, "a policy type", page_url),
                    url=urljoin(page_url, str(link["href"])),
                )
            )
    return awards


def normalise_product(policy_type: str, health_products: tuple[str, ...]) -> str | None:
    """Map a listed policy type to a health product, or ``None`` if it is not one.

    ``"Individual Mediclaim"`` becomes ``individual_mediclaim``; anything whose
    normalised form is not in ``health_products`` (``collect.sources.cioins.products``)
    is not a health award.
    """
    product = _slug(policy_type).replace("-", "_")
    return product if product in health_products else None


def doc_id_for(award: AwardLink) -> str:
    """Return ``cioins-<yyyy>-<mm>-<office code>-<award no>`` (runbook §6.1).

    The office is part of the identifier because award numbers repeat across offices.
    """
    return f"{SOURCE}-{award.award_date:%Y-%m}-{_slug(award.office)}-{_slug(award.award_no)}"


class CioinsCollector(Collector):
    """Collects CIOINS health awards; see the module docstring for the layout caveat."""

    source = SOURCE

    def iter_listed(self) -> Iterator[ListedDoc]:
        """Read the archive index and every month page; yield each award listed."""
        section = self.cfg.collect.sources.cioins
        index = self._listing(section.start)
        months = parse_archive_index(index.content, index.url)
        if not months:
            raise ListingChanged(
                f"no month links found on {section.start}; the page structure may have changed"
            )
        for month in months:
            page = self._listing(month.url)
            for award in parse_month_page(page.content, page.url):
                yield ListedDoc(
                    doc_id=doc_id_for(award),
                    url=award.url,
                    decision_date=award.award_date,
                    insurer=award.insurer,
                    product_listed=award.policy_type,
                    product=normalise_product(award.policy_type, section.products),
                    office=award.office,
                    # The outcome is only stated inside the award PDF; it is read in PR 5/6.
                    outcome_raw="",
                )

    def _listing(self, url: str) -> Response:
        """Fetch a listing page. Without it the run cannot know what exists, so it stops."""
        try:
            return self.session.get(url)
        except FetchFailed as exc:
            raise StopCollection(f"listing page could not be read ({exc.reason}): {url}") from exc
