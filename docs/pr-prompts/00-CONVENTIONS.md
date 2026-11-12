# ClaimSense — Conventions for every PR (read this first, Claude Code)

You are implementing ClaimSense one PR at a time. This file holds the rules that apply to **every** PR. The PR-specific file you were given holds the scope. Read both fully before writing code.

---

## 1. The project in one paragraph

ClaimSense predicts how an insurance ombudsman is likely to rule on a rejected health-insurance claim (`upheld` / `partially_upheld` / `rejected`), with a calibrated probability, the most similar **earlier** decisions as precedents, and an explanation in which every sentence cites a precedent. It is a fixed pipeline: collect → parse/segment → label/anonymise → dataset → fine-tuned classifier → calibration → retrieval → explanation → `predict()` → Streamlit app. No agents, no MCP.

## 2. Where the specs are (repo paths)

The specs already exist in the repo. **Read the spec docs named in your PR file before coding.** When the spec and the PR file disagree on behaviour, follow the spec and say so in the PR description. When they disagree on scope, follow the PR file.

| Area | Path |
|---|---|
| Overview, architecture, PR plan | `docs/01-project-overview.md`, `docs/02-architecture.md`, `docs/03-pr-plan.md`, `docs/planning/pr-plan.md` |
| Architecture contracts | `docs/architecture/{data-flow,data-schema,leakage-contract,pipeline-interface}.md` |
| Data | `docs/data/{terms-of-use-audit,collection-runbook,segmentation-rules,labelling-guide,anonymisation-spec,manual-audit-protocol,dataset-versioning}.md` |
| Modelling | `docs/modelling/{baselines,prompt-spec,finetuning-spec,experiment-log,calibration,retrieval-design,citation-checking,abstention-policy}.md` |
| Evaluation | `docs/evaluation/{evaluation-protocol,retrieval-rubric,error-taxonomy,fairness-analysis-plan,faithfulness-rubric}.md` |
| Operations | `docs/operations/{setup,configuration,ci-cd,reproduction,user-guide}.md` |
| Testing | `docs/testing/{test-strategy,leak-probe-tests,test-fixtures}.md` |
| Requirements | `docs/requirements/{PRD,scope,functional-requirements,non-functional-requirements,user-stories,acceptance-criteria}.md` |
| Responsible AI | `docs/responsible-ai/{limitations,privacy-impact-assessment,responsible-use}.md` |
| Planning | `docs/planning/{roadmap,risk-register,backlog-v2}.md` |

(PR 1 renames `docs/resposible-ai/` → `docs/responsible-ai/` and `functional-requirements (2).md` → `functional-requirements.md`. Before PR 1 merges, use the old names.)

## 3. Git workflow

1. Start from an up-to-date `main`: `git checkout main && git pull`.
2. Create the branch named in the PR file.
3. Commit in small, logical commits (Conventional Commits: `feat:`, `test:`, `chore:`, `docs:`, `fix:`).
4. Run `make pr-check` until it prints `ALL CHECKS PASSED`.
5. `git push -u origin <branch>`, then `gh pr create --base main --title "PR <N> · <title>" --body-file <filled template>`.
6. **Never merge.** Never push to `main`. Never use `--no-verify`, `[skip ci]`, `xfail` or `skip` to get a check green.
7. End commit messages and the PR body with the attribution lines your harness gives you, if any.

## 4. Hard rules

1. **Scope.** Build only what the PR file lists. Good ideas go to `docs/planning/backlog-v2.md` (one line each).
2. **No real data in git.** Nothing under `data/` (except `data/.gitkeep`, `data/README.md`), no real decision PDFs, no model weights except the LoRA adapter files PR 11 allows, no `.env`.
3. **No network in tests.** CI runs with `pytest-socket` blocking sockets and `HF_HUB_OFFLINE=1`. Websites, LLM APIs, NLI and embedding models are stubbed in `tests/stubs/`. Tests that truly need a real model are marked `slow`.
4. **One source of truth for numbers.** Every threshold, seed, path and model ID lives in `config.yaml`, read via `claimsense.config.load()`. Never copy a number into a module or a test.
5. **Leakage is a blocker.** A leak-probe failure is a real bug. Never weaken a probe; fix the code.
6. **No regressions.** Never delete, skip or weaken a test from an earlier PR. If an earlier test must change because a spec changed, explain why in the PR description. `scripts/pr_check.sh` fails if the collected test count drops below `tests/.test_count_floor`; raise the floor at the end of each PR to the new count.
7. **Privacy.** Committed fixtures are synthetic (or saved pages with no personal data, per `docs/testing/test-fixtures.md` §2). Every fixture is listed in `tests/fixtures/FIXTURES.yaml`.
8. **Type hints and docstrings** on every public function. `ruff` and `black` clean.
9. **Determinism.** Seeds come from config. Same inputs → same outputs (same dataset hash, same report bytes).

## 5. Cross-PR interfaces (keep these stable)

Later PRs depend on these names. If a spec doc defines a signature, the spec wins; otherwise use these.

| Module | Public API |
|---|---|
| `claimsense.config` | `load(path: Path | None = None) -> Config`; `config_hash(cfg) -> str` (only **V** keys); CLI `python -m claimsense.config show|check` |
| `claimsense.paths` | `data_dir()`, `raw_dir(source)`, `interim_dir()`, `processed_root()`, `processed_dir(version)`, `latest_processed()`, `models_dir()`, `index_dir()`, `reports_dir()`; all honour `CLAIMSENSE_DATA_DIR` / `CLAIMSENSE_OUT_DIR` |
| `claimsense.schema` | `LABELS = ("upheld", "partially_upheld", "rejected")` (this order everywhere), `SOURCES`, `COUNTRY_OF_SOURCE`, `RejectionReason` enum, record dataclasses per `docs/architecture/data-schema.md` |
| `claimsense.collect` | `PoliteSession(cfg, transport=None, clock=None)`; `Collector.run(max_docs=None, dry_run=False) -> RunStats`; `Manifest(path)` |
| `claimsense.parse` | `extract_text(path) -> ParsedDoc`; `segment(text, source, meta) -> Segments | Dropped` |
| `claimsense.label` | `extract_label(award_text, source) -> str` (label, `"EXCLUDE"`, or raises `UnmappedOutcome`); `Anonymiser.anonymise_record(rec) -> rec`; `pii_scan(records) -> list[Hit]` |
| `claimsense.dataset` | `build(cfg) -> BuildResult(version: str, path: Path)` |
| `claimsense.models` | `Classifier` protocol: `fit(train_df, val_df)`, `predict_proba(texts) -> np.ndarray (n, 3)`, `save(dir)`, `load(dir)`; `Calibrator.fit(logits, y)`, `.transform(logits) -> probs` |
| `claimsense.retrieve` | `PrecedentIndex.build(records, encoder, out_dir)`; `PrecedentIndex.load(dir)`; `.search(text, before: date, k, exclude_doc_id=None) -> list[Precedent]` |
| `claimsense.explain` | `Explainer.explain(facts, precedents) -> list[DraftSentence]`; `CitationChecker.filter(drafts, precedents) -> (kept, dropped)` |
| `claimsense.pipeline` | `load()`, `predict(...) -> PredictionResult` exactly per `docs/architecture/pipeline-interface.md` |

Heavy dependencies are **constructor arguments** (transport, clock, encoder, LLM client, NLI model, classifier), so tests swap in stubs without monkey-patching.

## 6. Test layout and markers

```text
tests/
├── unit/ collect/ leak/ integration/ pipeline/ app/ slow/ bench/
├── e2e/            # the growing end-to-end suite (§7)
├── stubs/          # fake_http, fake_clock, stub_llm, stub_nli, hashing_embedder, stub_classifier ...
├── fixtures/       # committed fixtures + FIXTURES.yaml
└── .test_count_floor
```

| Marker | Meaning | In `make test` / CI |
|---|---|---|
| *(none)* | unit, collector, integration, pipeline, app | ✅ |
| `leak` | leak probes, fixture mode | ✅ (own CI job) |
| `e2e` | end-to-end chain on the synthetic world | ✅ (own CI job, `make test-e2e`) |
| `local_data` | needs the real `data/processed/` or real artefacts; auto-skips with a reason | ❌ CI, ✅ `make test-data` |
| `slow` | loads a real heavy model | ❌ CI, ✅ `make test-slow` / `slow.yml` |

Every test file starts with a one-line docstring saying which FR/NFR/acceptance criterion it covers.

## 7. The end-to-end (e2e) suite

**Purpose.** Prove that every stage built so far still works **together**, on the outputs of the real earlier stages, offline, in under ~3 minutes.

```text
tests/e2e/
├── conftest.py      # session-scoped `world` fixture (E2EWorld): tmp root, env overrides, stage cache
├── corpus.py        # deterministic synthetic decisions + fake sites (PR 3, extended PR 4)
├── stages.py        # run_collect(world), run_parse(world), run_label(world), run_build(world), ...
└── test_e2e_NN_<stage>.py   # one file per PR that adds a stage
```

Rules:
1. `world` sets `CLAIMSENSE_DATA_DIR`, `CLAIMSENSE_OUT_DIR`, `CLAIMSENSE_ENV=ci`, `MLFLOW_TRACKING_URI` to a session tmp dir, and loads `config.yaml` merged with `tests/e2e/e2e_config.yaml` (small sizes, fast settings).
2. Each `run_<stage>(world)` calls the **real public API** of that stage, using only stubs for network/LLM/heavy models. It first calls the previous stage (cached per session), so stage N always consumes stage N-1's real output.
3. Each new e2e test file asserts: (a) the stage runs; (b) its outputs satisfy the contract the next stage needs (schema, file names, versions); (c) one or two invariants that cross stages (e.g. no findings text reaches `facts_text` after the whole chain; `dataset_version` is the same in every artefact).
4. Earlier e2e test files are never edited to fit new code, except when a spec changed (explain in PR).
5. `test_e2e_99_contracts.py` (added PR 7, extended later) checks version links across all artefacts that exist so far.

## 8. Commands that must exist (and grow)

| Target | Does |
|---|---|
| `make lint` / `make fmt` | ruff + black |
| `make test` | `pytest -m "not slow and not local_data and not e2e"` |
| `make test-leak` | `pytest tests/leak -m leak` |
| `make test-e2e` | `pytest tests/e2e -m e2e` |
| `make test-data` / `make test-slow` | as in `docs/testing/test-strategy.md` §4 |
| `make pr-check` | `bash scripts/pr_check.sh` — the pre-merge gate (§9) |

## 9. `scripts/pr_check.sh` (created in PR 1, extended by later PRs)

Runs, in order, and prints a PASS/FAIL table with a final `ALL CHECKS PASSED` or `CHECKS FAILED`:

1. `uv sync --frozen --all-extras` (lock still valid) and `requirements-lock.txt` matches `uv export`.
2. `make lint`.
3. `make test` with `CLAIMSENSE_ENV=ci HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=""` and `--disable-socket`.
4. `make test-leak` (from PR 6 it must collect ≥ 1 test).
5. `make test-e2e`.
6. `bash scripts/ci_guard.sh`.
7. Collected test count ≥ `tests/.test_count_floor`.
8. If `data/processed/LATEST` exists: `make test-data` (skips count as FAIL here).

## 10. PR description

Fill `.github/pull_request_template.md`. Always include: requirements covered (FR/NFR IDs), risks touched (R IDs), spec docs implemented, the `make pr-check` summary table, the new test count, and an empty **Manual checks** list copied from the PR file for Diya to complete.

## 11. When you are stuck

Stop and ask rather than guess when: a spec is ambiguous about behaviour that a later PR depends on; a test can only pass by weakening a guard; or the work needs real data, an API key or a GPU that you don't have. Mark anything you could not verify clearly in the PR description.
