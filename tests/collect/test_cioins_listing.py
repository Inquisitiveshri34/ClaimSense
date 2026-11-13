"""CIOINS collector (FR-01, FR-02, R14; runbook §6.1): listing pages, doc_id, product filter."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from claimsense import config, paths
from claimsense.collect.base import SourceDisabled
from claimsense.collect.cioins import (
    AwardLink,
    CioinsCollector,
    ListingChanged,
    doc_id_for,
    normalise_product,
    parse_archive_index,
    parse_month_page,
)
from claimsense.collect.manifest import (
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STATUS_FILTERED,
    STATUS_STORED,
    Manifest,
    manifest_path,
    raw_root,
    sha256_file,
)
from claimsense.config import Config
from tests.collect.helpers import (
    FIXTURES,
    assert_polite,
    base_url,
    crawl_delay_in,
    robots_url,
    run_collector,
)

CIOINS = FIXTURES / "cioins"
URLMAP = CIOINS / "urlmap.yaml"


def _urlmap() -> dict[str, str]:
    return yaml.safe_load(URLMAP.read_text(encoding="utf-8"))


def _url_serving(filename: str) -> list[str]:
    """The URLs the fake site maps to ``filename``, in file order."""
    return [url for url, served in _urlmap().items() if served == filename]


def _month_page(cfg: Config) -> list[AwardLink]:
    (page_url,) = _url_serving("month_2023-05.html")
    return parse_month_page((CIOINS / "month_2023-05.html").read_bytes(), page_url)


def test_archive_index_gives_month_urls(cioins_cfg: Config) -> None:
    start = cioins_cfg.collect.sources.cioins.start
    assert _url_serving("archive_index.html") == [start]

    months = parse_archive_index((CIOINS / "archive_index.html").read_bytes(), start)

    assert [(m.year, m.month) for m in months] == [(2023, 5), (2023, 6)]
    assert [m.url for m in months] == [
        *_url_serving("month_2023-05.html"),
        *_url_serving("month_empty.html"),
    ]
    assert all(m.url.startswith(base_url(cioins_cfg, "cioins")) for m in months)


def test_month_page_gives_award_links_with_offices(cioins_cfg: Config) -> None:
    awards = _month_page(cioins_cfg)

    assert [(a.office, a.award_no) for a in awards] == [
        ("Ahmedabad", "0056"),
        ("Ahmedabad", "0058"),
        ("Ahmedabad", "0077"),
        ("Bhopal", "0056"),
        ("Bhopal", "0061"),
    ]
    assert awards[0].award_date == date(2023, 5, 12)
    assert awards[0].insurer == "Fictional General Insurance Co. Ltd."
    assert awards[0].policy_type == "Individual Mediclaim"
    assert {a.url for a in awards} <= set(_urlmap()), "every award link is served by the fake site"


def test_same_award_number_in_two_offices_gives_two_doc_ids(cioins_cfg: Config) -> None:
    same_number = [a for a in _month_page(cioins_cfg) if a.award_no == "0056"]

    assert [a.office for a in same_number] == ["Ahmedabad", "Bhopal"]
    assert [doc_id_for(a) for a in same_number] == [
        "cioins-2023-05-ahmedabad-0056",
        "cioins-2023-05-bhopal-0056",
    ]


def test_empty_month_gives_no_rows_and_no_error() -> None:
    (page_url,) = _url_serving("month_empty.html")
    assert parse_month_page((CIOINS / "month_empty.html").read_bytes(), page_url) == []


def test_award_row_without_a_date_means_the_layout_changed() -> None:
    html = (CIOINS / "month_2023-05.html").read_text(encoding="utf-8")
    broken = html.replace('<td class="award-date">12.05.2023</td>', "")
    with pytest.raises(ListingChanged, match="date"):
        parse_month_page(broken, "test://month")


def test_product_filter(cioins_cfg: Config) -> None:
    products = cioins_cfg.collect.sources.cioins.products

    for product in products:
        listed = product.replace("_", " ").title()
        assert normalise_product(listed, products) == product
    assert normalise_product("Motor (Private Car Package)", products) is None
    assert normalise_product("Life", products) is None


def test_run_stores_health_awards_and_filters_the_rest(cioins_cfg: Config) -> None:
    stats, transport = run_collector(CioinsCollector, cioins_cfg, URLMAP)

    assert (stats.listed, stats.stored, stats.filtered, stats.duplicate, stats.failed) == (
        5,
        2,
        1,
        1,
        1,
    )
    assert stats.stopped is None
    products = cioins_cfg.collect.sources.cioins.products
    with Manifest(manifest_path(cioins_cfg)) as manifest:
        rows = manifest.rows("cioins")
        statuses = {entry.url: entry for entry in manifest.crawl_entries()}

    # FR-01a/b: files under raw/cioins/, every product a health product.
    assert [row.doc_id for row in rows] == [
        "cioins-2023-05-ahmedabad-0056",
        "cioins-2023-05-bhopal-0056",
    ]
    assert [row.office for row in rows] == ["Ahmedabad", "Bhopal"]
    for row in rows:
        stored = raw_root(cioins_cfg) / row.file_path
        assert stored.parent == paths.raw_dir("cioins", cioins_cfg)
        assert sha256_file(stored) == row.file_sha256  # FR-02b
        assert row.product in products
        assert row.mime_type == "application/pdf"
        assert date.fromisoformat(row.decision_date).year == 2023

    # award_nonhealth.pdf: filtered with a reason, and never requested.
    (nonhealth_url,) = _url_serving("award_nonhealth.pdf")
    assert statuses[nonhealth_url].status == STATUS_FILTERED
    assert "Motor" in (statuses[nonhealth_url].reason or "")
    assert nonhealth_url not in transport.urls()

    counts = sorted(entry.status for entry in statuses.values())
    assert counts == sorted(
        [STATUS_STORED, STATUS_STORED, STATUS_FILTERED, STATUS_DUPLICATE, STATUS_FAILED]
    )
    assert_polite(transport, cioins_cfg, min_gap=crawl_delay_in(CIOINS / "robots.txt"))
    assert transport.requests[0].url == robots_url(cioins_cfg, "cioins")


def test_index_without_month_links_stops_the_run(cioins_cfg: Config) -> None:
    start = cioins_cfg.collect.sources.cioins.start
    urlmap = {robots_url(cioins_cfg, "cioins"): "@404", start: "month_empty.html"}

    stats, _ = run_collector(CioinsCollector, cioins_cfg, urlmap, root=CIOINS)

    assert stats.stored == 0
    assert stats.stopped is not None and "no month links" in stats.stopped


def test_unreadable_listing_page_stops_the_run(cioins_cfg: Config) -> None:
    start = cioins_cfg.collect.sources.cioins.start
    urlmap = {robots_url(cioins_cfg, "cioins"): "@404", start: "@404"}

    stats, _ = run_collector(CioinsCollector, cioins_cfg, urlmap, root=CIOINS)

    assert stats.stopped is not None and "listing page" in stats.stopped


def test_disabled_source_refuses_to_run(
    cioins_cfg: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(config.OVERRIDE_ENV_VAR)
    repo_cfg = config.load()
    assert not repo_cfg.collect.sources.cioins.enabled, "CIOINS is not cleared in the repo config"

    with pytest.raises(SourceDisabled):
        run_collector(CioinsCollector, repo_cfg, URLMAP, dry_run=True)
    assert not manifest_path(repo_cfg).parent.joinpath("raw").exists()


def test_dry_run_lists_documents_and_writes_nothing(cioins_cfg: Config) -> None:
    stats, transport = run_collector(CioinsCollector, cioins_cfg, URLMAP, dry_run=True)

    assert stats.stored == 0
    assert len(stats.would_fetch) == 4  # every health award listed, including the dead link
    assert stats.filtered == 1
    assert transport.urls(".pdf") == []
    assert not paths.raw_dir("cioins", cioins_cfg).exists()
    with Manifest(manifest_path(cioins_cfg)) as manifest:
        assert manifest.rows() == [] and manifest.crawl_entries() == []


def test_max_docs_stops_after_that_many_new_documents(cioins_cfg: Config) -> None:
    stats, transport = run_collector(CioinsCollector, cioins_cfg, URLMAP, max_docs=1)

    assert stats.stored == 1
    assert len(transport.urls(".pdf")) == 1
    assert len(list(Path(paths.raw_dir("cioins", cioins_cfg)).glob("*.pdf"))) == 1
