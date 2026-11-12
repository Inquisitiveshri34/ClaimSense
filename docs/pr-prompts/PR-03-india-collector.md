# PR 3 · India collector (CIOINS) — risk checkpoint

| | |
|---|---|
| **Branch** | `feat/collect-cioins` |
| **Depends on** | PR 2 |
| **Covers** | FR-01–FR-03, NFR-08 · **Risks** R1, R14 |
| **Read first** | `docs/data/collection-runbook.md`, `docs/testing/test-fixtures.md` §1–§4, §8–§10, `docs/testing/test-strategy.md` §7–§8, `docs/architecture/data-schema.md` (manifest part), `docs/operations/configuration.md` §3.2 |
| **Done when** | A re-run downloads nothing new and the manifest has no gaps — proven offline by tests and e2e; real-run count recorded for the R1 checkpoint |

---

## 1. Goal

A polite, resumable collector for CIOINS health awards that writes a SQLite manifest, plus the shared collector machinery (session, manifest, CLI, fake transport) that PR 4 reuses. This PR also creates the **synthetic world** used by every later e2e test.

## 2. Files to add

| File | Contents |
|---|---|
| `src/claimsense/collect/base.py` | `PoliteSession(cfg, transport=None, clock=None)`: one connection; waits `max(min_interval_s, robots crawl-delay) + jitter` between requests using the injected clock; User-Agent from `collect.user_agent` (refuses to start if `contact_email` empty, unless `dry_run`); honours `Retry-After` on 429/503 else waits `backoff_base_s * 2**attempt`; 403 → `StopCollection`; stops after `stop_after_consecutive_failures`. `download(url, dest)` writes `dest.partial` then atomic rename; returns SHA-256 |
| `src/claimsense/collect/transport.py` | `Transport` protocol (`get(url, headers, timeout) -> Response`) and `RequestsTransport` |
| `src/claimsense/collect/manifest.py` | `Manifest(path)`: SQLite table with `doc_id` (deterministic: `<source>-<date>-<office>-<n>` or hash-based per spec), `source`, `url`, `decision_date`, `office`, `product`, `sha256`, `status` ∈ {stored, duplicate, filtered, failed}, `reason`, `fetched_at`; `upsert`, `has_url`, `has_hash`, `rows()`, `gaps()` |
| `src/claimsense/collect/cioins.py` | `CioinsCollector`: archive index → month pages → award links per office → product filter (`collect.sources.cioins.products`) → download to `raw_dir("cioins")`; skips URLs already `stored` |
| `src/claimsense/collect/__main__.py` | `python -m claimsense.collect run --source cioins [--max-docs N] [--dry-run]`, `verify` (re-hash every stored file; report missing/mismatched), `report` (counts by status, year, office) |
| `tests/stubs/fake_http.py` | Fake transport from `urlmap.yaml` (`"@404"`, `"@429:30"`, `"@503"`, `"@403"`, `"@timeout"`, `"@truncated"` directives); raises `UnmappedURL`; records `(timestamp, url, headers)` |
| `tests/stubs/fake_clock.py` | Monotonic clock whose `sleep()` advances time instantly |
| `tests/fixtures/collect/cioins/` | `urlmap.yaml`, `archive_index.html`, `month_2023-05.html`, `month_empty.html`, `award_text.pdf`, `award_scan.pdf`, `award_nonhealth.pdf`, `robots.txt` — **synthetic or saved-redacted only** (CIOINS is not cleared for redistribution) |
| `tests/fixtures/collect/http/responses.yaml` | Error-response scenarios |
| `tests/fixtures/_build/make_pdfs.py` | Deterministic PDFs from `.txt` sources with reportlab (fixed creation date, invariant metadata) so re-running yields byte-identical files |
| `tests/fixtures/FIXTURES.yaml` | Entries for every fixture (kind, origin, sha256, `contains_personal_data: false`, `used_by`) |
| `tests/test_fixtures_manifest.py` | Checks from `test-fixtures.md` §9 |
| `scripts/fixtures/capture.py`, `scripts/fixtures/redact_html.py` | One polite request capture; HTML redaction helper (not run in tests) |
| `tests/collect/test_cioins_listing.py`, `test_manifest_schema.py`, `test_resume.py`, `test_verify.py`, `test_politeness.py` | See §4 |
| `tests/e2e/corpus.py` | See §5 |

## 3. Files to modify

`config.yaml` (no new keys unless the spec needs one), `src/claimsense/config.py` (validation for any new keys), `scripts/ci_guard.sh` (allow URLs in `tests/fixtures/**/urlmap.yaml` and `tests/e2e/corpus.py` only), `Makefile` (`collect`, `verify-data` targets), `pyproject.toml` (`requests`, `beautifulsoup4`, `lxml`; test extra `reportlab`), `CHANGELOG.md`.

## 4. Tests to write

**`test_cioins_listing.py`**: archive index → expected month URLs; `month_2023-05.html` → expected award links with office codes, including the same award number in two offices → two distinct `doc_id`s; `month_empty.html` → 0 rows, no error; `award_nonhealth.pdf` → `filtered` with reason.

**`test_manifest_schema.py`**: columns and types; `status` constrained; `doc_id` unique; `decision_date` ISO date.

**`test_resume.py`** (all four scenarios in `test-fixtures.md` §4): second run `stored 0` and unchanged row count; transport failing after the 3rd document then re-run → complete, no duplicate `doc_id`/hash, no `.partial` left; tampered file → `verify` reports mismatch and next run re-downloads; two URLs same bytes → second `duplicate`.

**`test_verify.py`**: clean store → 0 problems; deleted file → `missing`; changed byte → `hash_mismatch`; `verify` exit code non-zero when problems exist.

**`test_politeness.py`**: on the fake clock no two requests are < `min_interval_s` apart; robots crawl-delay 5 raises the gap to ≥ 5; exactly one in-flight request; User-Agent contains version and contact email; 429 with `Retry-After: 30` waits ≥ 30; 503 without header backs off; 403 stops the run; 10 consecutive failures stop the run; empty `contact_email` → refuses to start (non-dry-run).

## 5. E2E — the synthetic world (`tests/e2e/corpus.py`)

Create a deterministic generator used by all later PRs:

- `build_corpus(root, seed) -> Corpus`: **90 synthetic decisions** (30 per source; this PR implements CIOINS, PR 4 adds FOS and FSPO behind the same function). Decision dates spread 2019-01 → 2025-12 so every split gets data. Labels balanced across `upheld` / `partially_upheld` / `rejected`. Rejection reasons cover every `RejectionReason` value once PR 4 defines them (use placeholder strings now).
- Each decision has all four sections with the headings each source really uses (see `docs/data/segmentation-rules.md`), fictional names/addresses/phones/policy numbers (so PR 6's anonymiser has work to do), and a **weak, learnable signal** in the facts (e.g. "diagnosed after the policy began" → mostly upheld; "did not disclose a condition diagnosed earlier" → mostly rejected) so models in PRs 9–11 can beat the majority class.
- Writes PDFs (CIOINS) to a served folder and generates `urlmap.yaml` + archive/month HTML pages so `CioinsCollector` + `FakeTransport` collect them exactly like the real site. Also returns the ground truth (`doc_id → label, sections, date`) for later e2e assertions.
- Everything generated into the session tmp dir at runtime, never committed.

`tests/e2e/stages.py`: add `run_collect(world, sources=("cioins",))` using the real CLI entry function with `FakeTransport` + `FakeClock`.

**`tests/e2e/test_e2e_03_collect_cioins.py`**:
- Collecting the world's CIOINS site stores 30 files (non-health fixtures filtered), manifest rows match ground truth, `verify` reports 0 problems.
- Running again → `stored 0`.
- Every stored file's sha256 is in the manifest; `raw_dir("cioins")` is inside `world.root` (nothing written to the repo's `data/`).

## 6. Definition of done

`make pr-check` → ALL CHECKS PASSED; raise the test-count floor. Paste `python -m claimsense.collect report` output from the e2e world into the PR description as an example.

## 7. Manual checks (Diya)

- [ ] Set your email in `configs/local.yaml` (git-ignored): `collect: {contact_email: "..."}`.
- [ ] **Only if CIOINS is cleared in `DATA_SOURCES.md`:** `CLAIMSENSE_CONFIG=configs/local.yaml uv run python -m claimsense.collect run --source cioins --max-docs 20`, run it again → `stored 0`; `make verify-data` → 0 problems.
- [ ] **R1 checkpoint:** after a full real run, record the number of usable Indian health awards in the PR. If it is below ~800, write in the PR that the plan switches to "train UK + IE, test India out-of-distribution" (`docs/planning/risk-register.md` R1).
