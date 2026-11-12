# PR 2 · Source audit

| | |
|---|---|
| **Branch** | `docs/data-sources` |
| **Depends on** | PR 1 |
| **Covers** | NFR-08, NFR-09 · **Risks** R2 |
| **Read first** | `docs/data/terms-of-use-audit.md`, `docs/04-data-sources.md`, `DATA_SOURCES.md`, `docs/operations/configuration.md` §3.2, `docs/operations/ci-cd.md` §3.4 |
| **Done when** | Every source has a recorded licence and usage decision, and the repo provably cannot track raw data |

---

## 1. Goal

Before any scraping, fix in config and in CI what may be collected and what must never be committed. Mostly docs + guard rules + a machine-readable source registry that later collectors read.

## 2. Files to add

| File | Contents |
|---|---|
| `src/claimsense/collect/sources.py` | `SourceInfo` dataclass (`name`, `country`, `base_url`, `robots_url`, `licence`, `redistribution_allowed: bool`, `audit_date`) and `SOURCE_REGISTRY` built from `config.yaml` → `collect.sources` + the audit decisions. No network code |
| `tests/unit/test_sources.py` | See §4 |
| `tests/unit/test_gitignore.py` | See §4 |

## 3. Files to modify

| File | Change |
|---|---|
| `DATA_SOURCES.md` | Make sure each of CIOINS, FOS, FSPO has: URL, terms of use (link + access date), robots.txt rules, crawl delay, licence, redistribution decision, `enabled` decision. If information is unknown, write `UNKNOWN — to verify` (do **not** invent licence terms); Diya fills these in |
| `docs/data/terms-of-use-audit.md` | Add a decision table that matches `DATA_SOURCES.md` exactly |
| `DATA_CARD.md` | Turn into a template with placeholders for PR 7 tables (keep any existing prose) |
| `.gitignore` | Explicit `data/raw/`, `data/interim/`, `data/processed/`, `data/cache/`, `data/manifests/`, `data/_pii_quarantine/`, `mlruns/` |
| `scripts/ci_guard.sh` | New rule `gitignore-covers-data`: `git check-ignore -q` on a sample path in each folder above; fail if any is not ignored |
| `config.yaml` | Add the `collect` block from `configuration.md` §3.2 with `contact_email: ""`; `enabled` values = the audit decisions (default: `fspo: true`, others `false` until cleared) |
| `src/claimsense/config.py` | Schema for `collect`: `min_interval_s >= 2.0`, `jitter_s >= 0`, `max_retries >= 0`, sources keyed by `SOURCES`. Mark `collect.sources.*.enabled`, `*.products`, `*.product_filter`, `fos.health_keywords` as **V** keys in the hash registry |
| `tests/unit/test_config.py` | Add `test_min_interval_floor` (1.5 → rejected) and `test_config_hash_covers_v_keys` (flipping `fspo.enabled` changes the hash; changing `timeout_s` does not) |
| `tests/unit/test_guard.py` | Add a case: removing `data/raw/` from `.gitignore` makes the guard fail |
| `CHANGELOG.md` | One line |

## 4. Tests to write

**`tests/unit/test_sources.py`**
- Registry has exactly the three sources, each with a country matching `schema.COUNTRY_OF_SOURCE`.
- A source with `redistribution_allowed=False` is reported by `SOURCE_REGISTRY.fixture_policy(name)` as `"synthetic-or-redacted-only"` (used by PR 3 fixture rules).
- Every source marked `enabled: true` in config has a non-UNKNOWN licence in the registry; otherwise loading raises `SourceNotCleared`.

**`tests/unit/test_gitignore.py`**
- For each of `data/raw/a.pdf`, `data/interim/a.json`, `data/processed/v1/train.parquet`, `data/cache/x`, `data/manifests/m.sqlite`, `mlruns/0/meta.yaml`, `.env`: `git check-ignore` succeeds.
- `data/README.md` and `data/.gitkeep` are **not** ignored.

## 5. E2E tests to write

**`tests/e2e/test_e2e_02_sources.py`**
- In the `world`, `config.load()` with the e2e override enables all three sources (add to `tests/e2e/e2e_config.yaml`: all `enabled: true`, `contact_email: "e2e@example.invalid"`, `min_interval_s: 2.0`) and the registry loads without `SourceNotCleared` because the e2e override also supplies test licence values.
- `config_hash` of the world config differs from the repo config's (proves V keys feed the hash).

Add `run_sources(world)` to `tests/e2e/stages.py`.

## 6. Definition of done

`make pr-check` → ALL CHECKS PASSED; raise `tests/.test_count_floor`.

## 7. Manual checks (Diya)

- [ ] Open each source's terms page and robots.txt yourself; replace every `UNKNOWN — to verify` in `DATA_SOURCES.md` with what you found and the date. Only set `enabled: true` for sources you are comfortable collecting from.
- [ ] Remove `data/raw/` from `.gitignore` locally → `bash scripts/ci_guard.sh` fails → restore.
