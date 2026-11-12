# ClaimSense — CI/CD

> The GitHub Actions setup: every workflow and job, what each runs, which jobs block a merge into `main`, how branch protection and the PR template enforce the PR rules, and what "delivery" means for a project that is never deployed as a service. The suite behind these jobs is described in `../testing/test-strategy.md`; this file covers the pipeline that runs it.

**Author:** Diya Shrivastava · **Owning PR:** 1 (workflows, branch protection, PR template); jobs switched on by later PRs as listed in §6 · **Status:** Planned

**Related:** NFR-05, NFR-08, NFR-10, `setup.md`, `configuration.md`, `reproduction.md`, `../testing/test-strategy.md` §5–§6, `../testing/leak-probe-tests.md`, `../planning/pr-plan.md` (PR rules), `../evaluation-protocol.md` §2, risks R3, R5, R14, R15.

---

## 1. Principles

1. **CI proves the code; the PR description proves the data.** CI runs on fixtures with no data and no network. Gates that need the real dataset or a human (leak probes on real data, PII audit, metrics) are run locally and pasted into the PR description (`test-strategy.md` §6).
2. **A red check is never bypassed.** No admin merges, no `[skip ci]` on PRs into `main`, no retry-until-green. A flaky test is fixed or deleted in the same PR.
3. **Leakage is visible by name.** Leak probes run as their own job, so a failure shows up as `leak` in the PR checks, not buried in a long test log.
4. **CI cannot leak data or secrets.** No secrets are configured for PR workflows, the network is blocked inside tests, and a guard job fails if data, weights or `.env` are tracked.
5. **No deployment.** v1 is a local app (`responsible-use.md` §4). "Delivery" is a tagged, reproducible release (§5), not a running service.

---

## 2. Workflows

| File | Trigger | Purpose | Blocks merge? |
|---|---|---|---|
| `.github/workflows/ci.yml` | `push` to any branch, `pull_request` into `main` | Lint, tests, leak probes, guard | ✅ |
| `.github/workflows/slow.yml` | `workflow_dispatch` (manual) | Tests that load real models (`make test-slow`) | ❌ (result pasted into PR 13, 16, 18) |
| `.github/workflows/release.yml` | Push of a tag `v*` | Re-run CI on the tag, build the package, create the GitHub Release | Not a merge check |

No scheduled workflows: nothing in ClaimSense should run unattended against the ombudsman sites or an LLM provider.

---

## 3. `ci.yml` jobs

### 3.1 Summary

| Job | Steps | Time budget | Required check | From PR |
|---|---|---|---|---|
| `lint` | Install from lock → `ruff check .` → `black --check .` → lock-export check | < 2 min | ✅ | 1 |
| `test` | Install from lock (CPU torch) + Tesseract → `pytest -m "not slow and not local_data"` with network blocked, GPU hidden | < 8 min | ✅ | 1 |
| `leak` | Install from lock → `pytest tests/leak -m leak` | < 3 min | ✅ | 6 |
| `guard` | Repository checks (§3.4); no install needed | < 1 min | ✅ | 1 (rules added in 2, 11) |

All four run in parallel. Merge requires **all four green on the PR's latest commit**.

### 3.2 Environment

| Setting | Value | Why |
|---|---|---|
| Runner | `ubuntu-24.04` | Same OS family as the WSL2 dev setup |
| Python | 3.11 (`actions/setup-python`) | NFR-05 |
| Installer | `astral-sh/setup-uv`, `uv sync --frozen --all-extras` | Exact lock-file versions; fails if the lock is stale |
| Cache | uv cache keyed on `uv.lock` hash | Install drops from minutes to seconds |
| `CLAIMSENSE_ENV` | `ci` | Stubs on, network block on |
| `HF_HUB_OFFLINE` | `1` | Forces every model in non-slow tests to be a stub or tiny fixture |
| `CUDA_VISIBLE_DEVICES` | `""` | Proves CPU-only paths (NFR-07b) |
| Secrets | **None** | CI never calls Groq, Gemini, W&B or Kaggle |
| Permissions | `contents: read` | Least privilege; only `release.yml` can write |
| Concurrency | `group: ci-${{ github.ref }}`, `cancel-in-progress: true` | A new push cancels the old run on the same branch |

### 3.3 Sketch of `ci.yml`

```yaml
name: ci
on:
  push:
  pull_request:
    branches: [main]
permissions:
  contents: read
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
env:
  CLAIMSENSE_ENV: ci
  HF_HUB_OFFLINE: "1"
  CUDA_VISIBLE_DEVICES: ""
  TOKENIZERS_PARALLELISM: "false"

jobs:
  lint:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with: {python-version: "3.11", enable-cache: true}
      - run: uv sync --frozen --all-extras
      - run: uv run ruff check .
      - run: uv run black --check .
      - name: requirements-lock.txt matches uv.lock
        run: |
          uv export --frozen --all-extras --no-hashes > /tmp/req.txt
          diff -u requirements-lock.txt /tmp/req.txt

  test:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - run: sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
      - uses: astral-sh/setup-uv@v5
        with: {python-version: "3.11", enable-cache: true}
      - run: uv sync --frozen --all-extras
      - run: >
          uv run pytest -m "not slow and not local_data"
          --disable-socket --allow-unix-socket
          --cov=src/claimsense --cov-report=term-missing --cov-report=xml
      - uses: actions/upload-artifact@v4
        if: always()
        with: {name: coverage, path: coverage.xml}

  leak:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with: {python-version: "3.11", enable-cache: true}
      - run: uv sync --frozen --all-extras
      - run: uv run pytest tests/leak -m leak --disable-socket -v

  guard:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - run: bash scripts/ci_guard.sh
```

Until PR 6 adds the first leak probe, the `leak` job runs `pytest tests/leak` against an empty directory and passes with "no tests collected" treated as success (`-o` setting in `pyproject.toml`). From PR 6 onward an **empty** leak run fails: `scripts/ci_guard.sh` asserts at least the five PR 6 probe files exist.

### 3.4 What `guard` checks (`scripts/ci_guard.sh`)

| Check | Fails when | Protects | From PR |
|---|---|---|---|
| No data tracked | Any tracked path under `data/` except `data/.gitkeep` and `data/README.md` | Raw and processed text, P-R5 | 1 |
| No PDFs | Any tracked `*.pdf` outside `tests/fixtures/` | Original decisions | 1 |
| No secrets file | `.env`, `kaggle.json` or `*.pem` tracked | Keys | 1 |
| `.gitignore` covers data | `data/raw/`, `data/interim/`, `data/processed/`, `data/cache/`, `mlruns/` not ignored | Accidental adds | 2 |
| No network in tests | `http://` or `https://` in `tests/` outside `tests/fixtures/**/url_map*.json` | R14, NFR-08 | 1 |
| No base weights | Any `*.safetensors`, `*.bin` or `*.pt` over 50 MB, or any weight file under `models/` other than `adapter_model.safetensors` / `head.safetensors` | Licence, repo size | 11 |
| Fixtures are synthetic | A file under `tests/fixtures/` lacks the `synthetic: true` header or matches a real `doc_id` pattern from the manifest | PII in fixtures (`test-fixtures.md` §2) | 6 |
| Leak probes present | Fewer than the PR 6 probe files in `tests/leak/` (after PR 6) | Silent deletion of a guard | 6 |
| Prompt files hashed | A file in `src/claimsense/prompts/` whose hash is not in the registry | Silent prompt edits (`prompt-spec.md` §1) | 10 |
| Protocol frozen | `docs/evaluation/evaluation-protocol.md` differs from tag `eval-protocol-v1` without a new row in its deviations log | Moving targets (`evaluation-protocol.md` §2) | 7 |

---

## 4. What blocks a merge into `main`

### 4.1 Automatic (branch protection)

| Rule on `main` | Setting |
|---|---|
| Required status checks | `lint`, `test`, `leak`, `guard`; "require branches to be up to date" on |
| Direct pushes | Blocked, including for the repo owner |
| History | Linear (squash merge only); merge commits disabled |
| Force push / deletion | Blocked |
| Conversation resolution | Required (self-review comments must be resolved) |
| Signed commits | Not required |

### 4.2 Manual (PR template)

`.github/pull_request_template.md` must be filled before merging. A box left unticked, or a pasted result missing, blocks the merge by rule even though GitHub cannot enforce it.

```markdown
## PR <N> · <title>
Branch: `<branch>` · Spec: `<doc>` · Done when: <copied from pr-plan.md>

### Requirements and risks
- FR / NFR covered: 
- Risks touched (R-IDs): 

### Done-when evidence
- [ ] CI run: <link>
- [ ] Local data gate (if any): `make test-data` summary line pasted below
- [ ] Manual audit (if any): audit ID + result
- [ ] Metrics (if any): run IDs + numbers (copied by export script, not typed)

### Acceptance criteria (from acceptance-criteria.md §4 for this PR)
- [ ] …

### Scope check
- [ ] Nothing here is outside this PR's deliverables in pr-plan.md (new ideas → backlog-v2.md)
- [ ] No data, weights or secrets added
- [ ] Docs updated where this PR changes a spec
```

### 4.3 Blocking matrix

| Situation | Merge? |
|---|---|
| Any required check red | ❌ |
| Required checks green, but a `local_data` gate claimed by the PR was **skipped** | ❌ (a skip is not a pass, `test-strategy.md` §4) |
| Leak probe marked `skip` or `xfail` | ❌ (`test-strategy.md` §1, principle 6) |
| Coverage dropped below 85% on core modules | ✅ allowed, but the PR description says why (not a hard gate) |
| `slow.yml` not run on a PR that needs it (13, 16, 18) | ❌ by PR template |
| Done-when check unmet, everything else green | ❌ (PR rule 1) |

---

## 5. `slow.yml` and `release.yml`

### 5.1 `slow.yml` (manual)

| Step | Detail |
|---|---|
| Trigger | Actions tab → *slow* → *Run workflow* on the PR branch |
| Network | Allowed (model downloads); `HF_HUB_OFFLINE` unset |
| Cache | `~/.cache/huggingface` keyed on the pinned model revisions in `config.yaml` |
| Runs | `make test-slow` (real NLI cross-encoder drops an injected unsupported sentence, etc.) |
| Result | Link pasted into PRs 13, 16 and 18, and after any change to `cite_check.model` |

### 5.2 `release.yml` (on tag)

The only workflow with `contents: write`.

| Step | Detail |
|---|---|
| 1 · Re-run checks | Calls the `ci.yml` jobs as a reusable workflow on the tagged commit; stops if any fails |
| 2 · Check tag | Tag matches `project.version` in `config.yaml` and `pyproject.toml` |
| 3 · Build | `uv build` → wheel + sdist |
| 4 · Release notes | Body generated from `CHANGELOG.md`'s section for the tag + the README results table |
| 5 · Attach | Wheel, sdist, `SHA256SUMS`; the LoRA adapter, calibrator and `thresholds.json` **only if** the PR 18 release decision says weights are published (`terms-of-use-audit.md` §6) |
| 6 · Never | Uploads data, the processed dataset or the precedent index text; publishes to PyPI; deploys anything |

The release workflow does **not** train or evaluate. Training needs a GPU and the private dataset, and evaluation needs the dataset; both are run by the author and proved by `reproduction.md`. The release only packages what was already verified.

### 5.3 Tagging

```bash
git checkout main && git pull
git tag -a v1.0.0 -m "ClaimSense v1.0.0"
git push origin v1.0.0
```

Other tags in use: `eval-protocol-v1` (PR 7, frozen evaluation plan). Tags are never moved or deleted.

---

## 6. Jobs and rules switched on per PR

| PR | CI change |
|---|---|
| 1 | `ci.yml` with `lint`, `test`, `guard` (data, PDF, secrets, URL rules); placeholder test; branch protection; PR template; pre-commit config mirrors `lint` |
| 2 | `guard`: `.gitignore` covers data folders |
| 3–4 | Collector tests on saved pages join `test`; Tesseract install step added for PR 5 |
| 6 | `leak` job required; `guard`: fixtures synthetic, leak probes present |
| 7 | `guard`: evaluation protocol frozen at `eval-protocol-v1`; dataset-hash rebuild test joins `test` |
| 10 | `guard`: prompt files hashed |
| 11 | `guard`: no base weights; adapter `meta.json` schema test |
| 13 | `slow.yml` added (real NLI model) |
| 14 | `test_report_command.py` (report builds on the mini-dataset) joins `test` |
| 16 | Pipeline tests join `test`; `make bench` result pasted, not run in CI |
| 17 | Streamlit `AppTest` page tests join `test` |
| 18 | `release.yml` added; first tag `v1.0.0` |

---

## 7. Local mirror: pre-commit

`.pre-commit-config.yaml` runs the fast parts of CI before each commit, so most failures never reach GitHub.

| Hook | Mirrors |
|---|---|
| `ruff` (with `--fix`), `black` | `lint` |
| `check-added-large-files` (500 KB) | `guard` (weights, PDFs) |
| Local hook `block-data-paths` | `guard` (`data/`, `*.pdf`, `.env`, `_pii_quarantine/`) |
| `detect-private-key` | `guard` (secrets) |
| `check-yaml`, `end-of-file-fixer`, `trailing-whitespace` | Hygiene |

`pre-commit run --all-files` before pushing a large change. Never commit with `--no-verify`.

---

## 8. When CI fails

| Failing job | First thing to check | Typical fix |
|---|---|---|
| `lint` | `make fmt` locally | Formatting; or `uv.lock` changed without re-exporting `requirements-lock.txt` |
| `test`: `SocketBlockedError` | A test reached the network | Add the saved page or stub (`test-fixtures.md`) |
| `test`: model download error | `HF_HUB_OFFLINE=1` blocked a real model | Use the stub, or mark the test `slow` |
| `test`: collector parser fails | Saved page changed, or the parser regressed (R14) | Fix the parser; add the new page as an extra fixture, keep the old one |
| `leak` | Answer text reached `facts_text`, or a split leaked | **Treat as a real leak.** Fix the segmenter or split; add a planted-violation fixture for the bug |
| `guard` | Something sensitive is tracked | `git rm --cached <path>`; if it was ever pushed, rewrite history and rotate any exposed key |
| Any job, intermittently | Flaky test | Fix or delete in the same PR; never add retries |
