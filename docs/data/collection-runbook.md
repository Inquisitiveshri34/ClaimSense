# ClaimSense — Collection Runbook

> How to run the three collectors: prerequisites, commands, how resuming works, the rate-limit rules, what each failure means and what to do about it. Written so a fresh clone can collect the same data the same way.

**Author:** Diya Shrivastava · **Owning PR:** 3 (CIOINS), 4 (FOS, FSPO) · **Status:** Planned

**Related:** `terms-of-use-audit.md` (must be cleared first), `data-flow.md` §2 Stage 1, `data-schema.md` §2 (manifest), NFR-08, FR-01–03.

---

## 1. Before you run anything

| Check | Where | Blocks run if |
|---|---|---|
| Source cleared in the terms audit | `terms-of-use-audit.md` §4, §6 | Any box for that source is unticked or permission is pending |
| robots.txt captured within the last 3 months | `terms-of-use-audit.md` §3, §8 | Older or missing |
| Contact email set | `config.yaml` → `collect.contact_email` | Empty |
| `data/raw/` and `data/manifests/` git-ignored | `.gitignore` | Not ignored |
| Disk space | ≥ 5 GB free | Less |
| Collector tests pass on saved pages | `pytest tests/collect/` | Any failure (site may have changed, risk R14) |

As of the first audit (2026-11-12) **only FSPO is cleared.** CIOINS and FOS collectors are built and tested against saved fixtures but not run live.

---

## 2. Configuration (`config.yaml`)

```yaml
collect:
  contact_email: "<your email>"
  user_agent: "ClaimSense/{version} (non-commercial research; contact: {contact_email})"
  min_interval_s: 3.0        # NFR-08: never below 2.0; raised to robots Crawl-delay if higher
  jitter_s: 0.5              # random 0–0.5 s added to each wait
  timeout_s: 30
  max_retries: 3
  backoff_base_s: 10         # 10, 20, 40 s between retries after a timeout or 5xx
  retry_after_default_s: 300 # wait after 429/503 when the site sends no Retry-After
  stop_after_consecutive_failures: 10
  sources:
    cioins:
      enabled: false         # flip only after terms-of-use-audit clears it
      start: "https://cioins.co.in/AwardsHArchive"
      products: [individual_mediclaim, group_mediclaim, overseas_mediclaim]
    fos:
      enabled: false
      product_filter: "Insurance"
      health_keywords: [medical, health, hospital, surgery, treatment, "private medical", "critical illness"]
    fspo:
      enabled: true
      product_filter: "Health, Accident and Other"
```

`health_keywords` decides which FOS decisions count as health. The list is fixed per dataset version; changing it means a new version (`dataset-versioning.md` §4).

---

## 3. Commands

```bash
# one source, full run (resumes automatically); same as: make collect SOURCE=fspo
python -m claimsense.collect run --source fspo

# dry run: fetch the listings, list what would be downloaded, write nothing
python -m claimsense.collect run --source fspo --dry-run

# limit for a smoke test: stop after 20 new documents
python -m claimsense.collect run --source fspo --max-docs 20

# check the store against the manifest (exit code 1 on any problem); same as: make verify-data
python -m claimsense.collect verify

# report: counts by status (crawl_log), decision year and office (manifest)
python -m claimsense.collect report
```

A run refuses to start if the source has `enabled: false`, if its licence is still unknown, or (unless `--dry-run`) if `collect.contact_email` is empty. Put your email in a git-ignored override file and name it in `CLAIMSENSE_CONFIG`:

```bash
echo 'collect: {contact_email: "you@example.org"}' > configs/local.yaml
CLAIMSENSE_CONFIG=configs/local.yaml python -m claimsense.collect run --source fspo --max-docs 20
```

Not built yet: a `--from/--to` date window (needed for FOS, PR 4), `--refilter`, and a per-run log file.

Each run ends with a one-line summary:

```text
fspo: listed 1,240 · stored 1,102 · filtered 121 · duplicate 9 · failed 8 · skipped(already have) 0 · 01:12:40
```

Paste that summary into the PR description (FR-01c).

---

## 4. Rate limits and politeness (NFR-08)

| Rule | Value | Enforced by |
|---|---|---|
| Wait between any two requests to the same host | `max(min_interval_s, robots Crawl-delay)` + jitter | `PoliteSession` in `collect/base.py`, the single shared limiter |
| Concurrency | 1 worker, 1 connection | No thread or async pool in collectors |
| User-Agent | Project name, version, contact email | Set once in the session |
| robots.txt | Read once per host before the first request; a disallowed path is never requested | `PoliteSession` |
| Retries | ≤ `max_retries` (3) per URL; after a timeout, a cut-off body or a 5xx wait `backoff_base_s` × 2ⁿ (10, 20, 40 s) | `PoliteSession` |
| Respect `429` / `503` | Honour `Retry-After`; if absent, wait `retry_after_default_s` (5 minutes) | `PoliteSession` |
| Hard stop | A `403`, or 10 consecutive failed requests (`stop_after_consecutive_failures`) → stop the run | `PoliteSession` |
| Time of day | Prefer the publisher's night-time (India 00:00–06:00 IST; UK/IE 00:00–06:00 local) | Operator |

Never run two collectors against the same host at the same time. Running FOS and FSPO together is fine (different hosts).

---

## 5. How resuming works (FR-03)

1. Listing pages are read again on every run (a few requests), so new documents are found. Before fetching a **document**, the collector checks `crawl_log`; a URL with status `filtered` or `duplicate` is skipped.
2. Before fetching a document, it checks `manifest.doc_id`; if present **and** the file on disk hashes to `file_sha256`, it is skipped.
3. A file is first written to `data/raw/<source>/.partial/`, hashed, then moved into place, and only then is the manifest row inserted (one transaction). An interrupted run therefore leaves at most a stray `.partial` file, never a manifest row without a file.
4. `failed` URLs are retried on the next run; `filtered` URLs are not, unless `--refilter` is passed (used when keyword lists change).

**Check after any run:** `python -m claimsense.collect verify` recomputes every hash, reports rows without files, files without rows and leftover `.partial` files. It must report zero problems before PR 3/4 merge.

---

## 6. Per-source notes

### 6.1 CIOINS (PR 3)

| Step | Detail |
|---|---|
| Index | Health archive lists months; each month lists award PDFs per office |
| `doc_id` | `cioins-<yyyy>-<mm>-<office code>-<award no>` |
| Filter | Policy type from the listing or the award header; non-health dropped as `filtered` |
| Known quirks | Office layouts differ; some PDFs are scans (OCR in PR 5); award numbers may repeat across offices, hence the office code in `doc_id` |

### 6.2 FOS (PR 4)

| Step | Detail |
|---|---|
| Index | Decisions search, product = Insurance, paged |
| Metadata kept from listing | Date, business name, product, outcome (Upheld / Not upheld) |
| Filter | Health keywords in title/summary first; ambiguous ones fetched and checked in full text |
| `doc_id` | `fos-<yyyy>-<mm>-<FOS reference>` |
| Known quirks | Very large volume: always use `--from/--to` windows; provisional decisions quoted inside final decisions (handled in PR 5) |

### 6.3 FSPO (PR 4)

| Step | Detail |
|---|---|
| Index | Decisions filtered to "Health, Accident and Other" |
| Metadata kept | Outcome (4 values), conduct complained of, year, product |
| `doc_id` | `fspo-<yyyy>-<mm>-<FSPO reference>` |
| Known quirks | Metadata page precedes decision text in the PDF; parser must not treat it as facts (PR 5) |

---

## 7. Failures and what to do

| Symptom | Likely cause | Action |
|---|---|---|
| `403` on every request | Blocked or User-Agent rejected | **Stop.** Do not rotate agents or IPs. Re-check robots.txt and contact the publisher |
| `429` / `503` | Too fast or site busy | Collector backs off automatically; if it repeats, raise `min_interval_s` |
| `404` on a listed document | Link rot | Logged `failed`; leave it, note the count |
| Listing returns 0 items | Site structure changed (R14) | Collector tests on saved pages should catch it; update parser, add a new fixture |
| PDF hash already in manifest | Same file under two URLs | Logged `duplicate`; expected |
| `verify` reports rows without files | Manual deletion | Delete those rows and re-run |
| Disk full | — | Stop, clear `.partial/`, free space, re-run |

Never "fix" a block by evading it. A block is a signal to ask, not to work around.

---

## 8. After a collection run

1. `python -m claimsense.collect verify` → 0 problems.
2. `python -m claimsense.collect report` → paste counts into the PR.
3. Second run of the same command → `stored 0` (FR-03a).
4. Append the Collect row to `reports/funnel.csv` (`data-flow.md` §3).
5. Do **not** commit anything under `data/`.
