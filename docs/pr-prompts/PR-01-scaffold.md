# PR 1 · Repo scaffold

| | |
|---|---|
| **Branch** | `chore/scaffold` (from `main`) |
| **Depends on** | nothing (repo currently holds only docs) |
| **Covers** | NFR-05, NFR-10 |
| **Read first** | `docs/02-architecture.md` §5, `docs/operations/setup.md`, `docs/operations/configuration.md` §1–§2, §3.1, §5, `docs/operations/ci-cd.md`, `docs/testing/test-strategy.md` §1–§5 |
| **Done when** | CI is green on a placeholder test, and `make pr-check` passes on a fresh clone with no data and no API keys |

---

## 1. Goal

Turn the docs-only repo into a fully wired Python project: install, config, lint, tests, CI, guard, pre-merge script and the empty e2e harness all work **before any feature code exists**. Every later PR plugs into what this PR creates.

## 2. Current repo state

`main` contains `docs/` (spec docs in sub-folders), `reports/*.md`, and root `CHANGELOG.md`, `DATA_CARD.md`, `DATA_SOURCES.md`, `LICENSE`, `MODEL_CARD.md`, `README.md`. These root files and reports are **planned content**; leave their text alone in this PR except where listed below.

## 3. Housekeeping (first commit)

- `git mv docs/resposible-ai docs/responsible-ai`
- `git mv "docs/requirements/functional-requirements (2).md" docs/requirements/functional-requirements.md`
- Fix every link to the old names (`grep -rn "resposible-ai\|functional-requirements (2)" docs *.md`).

## 4. Files to add

| File | Contents |
|---|---|
| `pyproject.toml` | Package `claimsense`, src layout, `requires-python = ">=3.11,<3.12"`. Extras: `dev` (ruff, black, pre-commit, nbclient later), `test` (pytest, pytest-cov, pytest-socket, hypothesis), `train` (empty for now). Ruff + black config (line length 100). Pytest: `testpaths = ["tests"]`, `--strict-markers`, markers `leak`, `local_data`, `slow`, `e2e`. uv index override pinning the **CPU** wheel of torch for later (add the `[tool.uv]` block now, torch itself is added in PR 10) |
| `uv.lock`, `requirements-lock.txt` | `uv lock`; `uv export --frozen --all-extras --no-hashes > requirements-lock.txt` |
| `src/claimsense/__init__.py` | `__version__ = "1.0.0"` |
| `src/claimsense/config.py` | Pydantic v2 models for `project` and `paths`; `load()` reads `config.yaml`, deep-merges the file in `CLAIMSENSE_CONFIG` if set, validates (unknown keys → error, `extra="forbid"`); `config_hash(cfg)` = SHA-256 of canonical JSON of keys tagged **V** (registry list, empty for now); `python -m claimsense.config show [--section X]` and `check` (exit 1 on error) |
| `src/claimsense/paths.py` | Functions in `00-CONVENTIONS.md` §5; base dirs from config, overridden by `CLAIMSENSE_DATA_DIR` / `CLAIMSENSE_OUT_DIR` |
| `src/claimsense/schema.py` | `LABELS`, `SOURCES = ("cioins","fos","fspo")`, `COUNTRY_OF_SOURCE = {"cioins":"IN","fos":"GB","fspo":"IE"}`; more is added in PR 4 |
| `src/claimsense/{collect,parse,label,dataset,models,retrieve,explain,evaluate}/__init__.py` | Empty sub-packages |
| `config.yaml` | `project` and `paths` sections exactly as `docs/operations/configuration.md` §3.1 |
| `.env.example` | As `configuration.md` §5.3 |
| `.gitignore` | `.venv/`, `.env`, `data/*` with `!data/.gitkeep` `!data/README.md`, `models/**` weights, `index/`, `mlruns/`, `configs/local.yaml`, `tests/fixtures_local/`, `.pytest_cache/`, `coverage.xml`, `__pycache__/` |
| `.pre-commit-config.yaml` | As `ci-cd.md` §7 (ruff `--fix`, black, check-added-large-files 500 KB, detect-private-key, check-yaml, end-of-file-fixer, trailing-whitespace, local hook `block-data-paths`) |
| `scripts/block_data_paths.py` | Used by the local hook: rejects staged paths under `data/` (except the two allowed), `*.pdf` outside `tests/fixtures/`, `.env`, `kaggle.json`, `*.pem` |
| `scripts/ci_guard.sh` | PR 1 rules from `ci-cd.md` §3.4: no data tracked, no PDFs outside fixtures, no secrets files, no `http(s)://` in `tests/` outside `tests/fixtures/**/urlmap*.yaml` and `tests/e2e/corpus.py`. Each rule prints its name and PASS/FAIL; script exits non-zero if any fails |
| `scripts/pr_check.sh` | As `00-CONVENTIONS.md` §9. Steps 4 and 8 tolerate "no tests collected" / "no data" for now |
| `Makefile` | `lint`, `fmt`, `test`, `test-leak`, `test-e2e`, `test-data`, `test-slow`, `pr-check`, all via `uv run` |
| `.github/workflows/ci.yml` | Jobs `lint`, `test`, `leak`, `e2e`, `guard` per `ci-cd.md` §3.3; `e2e` job = `uv run pytest tests/e2e -m e2e --disable-socket`. Exit code 5 (no tests collected) is treated as success for `leak` only until PR 6 |
| `.github/pull_request_template.md` | As `ci-cd.md` §4.2, plus sections "make pr-check summary", "Test count", "Manual checks" |
| `tests/conftest.py` | `cfg` fixture (`config.load()`); autouse seed fixture; when `CLAIMSENSE_ENV=ci`, assert sockets are disabled; `local_data` auto-skip hook with the reason text from `test-strategy.md` §4 |
| `tests/unit/test_config.py` | See §6 |
| `tests/unit/test_paths.py` | See §6 |
| `tests/unit/test_schema_enums.py` | `LABELS` order and contents; every source has a country |
| `tests/test_placeholder.py` | Proves pytest runs |
| `tests/e2e/conftest.py` | `world` session fixture (`E2EWorld`): tmp root, sets env vars, writes merged config, exposes `world.cfg`, `world.root`, `world.cache: dict` |
| `tests/e2e/e2e_config.yaml` | Empty override for now (later PRs add small/fast settings) |
| `tests/e2e/stages.py` | Module docstring explaining the stage pattern; `run_scaffold(world)` returns resolved config |
| `tests/e2e/test_e2e_01_scaffold.py` | See §7 |
| `tests/.test_count_floor` | The collected test count after this PR |
| `tests/{collect,leak,integration,pipeline,app,slow,bench,fixtures,stubs}/.gitkeep` | Empty dirs |
| `data/.gitkeep`, `data/README.md` | Explains `raw/`, `interim/`, `processed/`, `manifests/`, `cache/`; never committed |

## 5. Files to modify

| File | Change |
|---|---|
| `README.md` | Add a "Development setup" section (the `setup.md` §3.1 commands + `make pr-check`) near the top; keep the rest |
| `CHANGELOG.md` | `## [Unreleased]` → "Repo scaffold, config, CI, e2e harness" |
| `docs/operations/setup.md` | Fix the clone URL to `https://github.com/Inquisitiveshri34/ClaimSense.git` |

## 6. Tests to write

**`tests/unit/test_config.py`**
- `test_loads_and_validates`: `config.yaml` parses; `cfg.project.name == "claimsense"`.
- `test_unknown_key_rejected`: a temp config with an extra key raises `ValidationError` naming the key.
- `test_override_merge`: a temp override changing `project.seed` changes only that key.
- `test_no_secrets`: no key name containing `key`, `token` or `secret` has a non-empty value.
- `test_config_hash_stable`: same config → same hash; changing a runtime-only key does not change it.
- `test_cli_check_exit_codes`: `python -m claimsense.config check` returns 0; with a broken `CLAIMSENSE_CONFIG` returns 1.

**`tests/unit/test_paths.py`**
- Defaults resolve under the repo root; `CLAIMSENSE_DATA_DIR` and `CLAIMSENSE_OUT_DIR` override them; `processed_dir("abc")` ends with `processed/vabc` (or the naming in `docs/data/dataset-versioning.md`, which wins).

**`tests/unit/test_guard.py`** (runs the shell script in a temp git repo)
- Clean repo → exit 0.
- Tracked `data/raw/x.txt` → non-zero with the rule name in output.
- Tracked `.env` → non-zero.
- Tracked `a.pdf` at root → non-zero; `tests/fixtures/a.pdf` → allowed.
- A test file containing `https://example.org` → non-zero.

## 7. E2E tests to write

**`tests/e2e/test_e2e_01_scaffold.py`** (marker `e2e`)
- `world` creates its tmp dirs and every `paths.*()` function points inside `world.root`.
- `python -m claimsense.config show` in a subprocess with the world's env prints the world paths.
- Every sub-package imports (`importlib.import_module` over the list).

## 8. Definition of done

```bash
uv sync --frozen --all-extras
make lint && make test && make test-e2e && bash scripts/ci_guard.sh
make pr-check        # ALL CHECKS PASSED
```

Push, open the PR, confirm CI shows `lint`, `test`, `leak`, `e2e`, `guard` green.

## 9. Manual checks (Diya, before merge)

- [ ] Fresh clone in a new folder → `uv sync --frozen --all-extras && make pr-check` → passes.
- [ ] `git add -f` a dummy `data/raw/x.txt` and try to commit → blocked by pre-commit. Undo.
- [ ] After merging: GitHub → Settings → Branches → protect `main`: required checks `lint`, `test`, `leak`, `e2e`, `guard`; require up to date; squash merge only; block force pushes; require conversation resolution.
