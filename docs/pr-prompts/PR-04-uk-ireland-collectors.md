# PR 4 · UK + Ireland collectors (FOS, FSPO)

| | |
|---|---|
| **Branch** | `feat/collect-fos-fspo` |
| **Depends on** | PR 3 |
| **Covers** | FR-01–FR-03, FR-02(c), NFR-08 · **Risks** R14 |
| **Read first** | `docs/data/collection-runbook.md` (FOS, FSPO sections), `docs/architecture/data-schema.md`, `docs/testing/test-fixtures.md` §4, `docs/operations/configuration.md` §3.2 |
| **Done when** | All three collectors write to one manifest schema, proven by tests and the e2e world |

---

## 1. Goal

Add FOS (insurance decisions filtered to health) and FSPO (health decisions, with outcome and conduct metadata) collectors on top of PR 3's machinery, and finish the shared record schema in `claimsense.schema`.

## 2. Files to add

| File | Contents |
|---|---|
| `src/claimsense/collect/fos.py` | `FosCollector`: pages search listing filtered to `product_filter: Insurance` until the last page; keeps listing metadata (date, product, outcome text); health filter on `health_keywords` in title/summary; ambiguous items fetched and checked on full text; non-health → `filtered` |
| `src/claimsense/collect/fspo.py` | `FspoCollector`: list filtered to `Health, Accident and Other`; stores `source_outcome` and `source_conduct` metadata; handles the metadata page before decision text |
| `tests/fixtures/collect/fos/` | `urlmap.yaml`, `search_p1.html`, `search_p2.html`, `search_last.html`, `decision_health.html`, `decision_motor.html`, `robots.txt` |
| `tests/fixtures/collect/fspo/` | `urlmap.yaml`, `list_p1.html`, `list_p2.html`, `decision_health.pdf`, `robots.txt` |
| `tests/collect/test_fos_listing.py`, `tests/collect/test_fspo_listing.py` | See §4 |

## 3. Files to modify

| File | Change |
|---|---|
| `src/claimsense/collect/manifest.py` | Nullable `source_outcome`, `source_conduct`, `title` columns; schema migration for existing manifests (add columns if missing) |
| `src/claimsense/collect/__main__.py` | `--source cioins|fos|fspo|all`; `report` grouped by source |
| `src/claimsense/schema.py` | `RejectionReason` enum, `InsurerType` enum and the manifest/record dataclasses from `docs/architecture/data-schema.md` |
| `tests/collect/test_manifest_schema.py` | `test_shared_schema`: rows from all three collectors validate against one schema and coexist in one SQLite file |
| `tests/unit/test_schema_enums.py` | Enum values exactly match `data-schema.md` |
| `tests/e2e/corpus.py` | Add 30 FOS (HTML) + 30 FSPO (PDF with metadata page) synthetic decisions, plus non-health distractors (motor) that must be filtered; real `RejectionReason` values |
| `tests/fixtures/FIXTURES.yaml`, `CHANGELOG.md` | Entries |

## 4. Tests to write

**`test_fos_listing.py`**: page 1 → page 2 → last page then stop (no request beyond last); listing metadata parsed (date, product, outcome); `decision_motor.html` → `filtered`; ambiguous listing item triggers exactly one full-text fetch; politeness assertions reused from PR 3 helpers.

**`test_fspo_listing.py`**: product filter applied; `source_outcome` / `source_conduct` stored; metadata page skipped when locating decision text start (store offset or flag for PR 5); resume works (second run `stored 0`).

## 5. E2E tests

`run_collect(world)` default becomes `sources=("cioins","fos","fspo")`.

**`tests/e2e/test_e2e_04_collect_all.py`**:
- All three sites collected into one manifest: 90 `stored`, all distractors `filtered`, 0 `failed`.
- `doc_id`s unique across sources; every row's `source` maps to the right country.
- Second full run → `stored 0` for all sources.
- `test_e2e_03_collect_cioins.py` still passes unchanged (regression).

## 6. Definition of done

`make pr-check` → ALL CHECKS PASSED; raise the floor.

## 7. Manual checks (Diya)

- [ ] FSPO (cleared): `run --source fspo --max-docs 20` twice → second `stored 0`; `make verify-data` clean.
- [ ] FOS only if cleared in `DATA_SOURCES.md`.
- [ ] Paste `python -m claimsense.collect report` from your real run.
