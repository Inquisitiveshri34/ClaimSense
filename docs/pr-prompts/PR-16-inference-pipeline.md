# PR 16 · Inference pipeline — `predict()`

| | |
|---|---|
| **Branch** | `feat/pipeline` |
| **Depends on** | PR 15 |
| **Covers** | FR-14, FR-17, NFR-06, NFR-07(b) · **Risks** R12 |
| **Read first** | `docs/architecture/pipeline-interface.md` (**the contract — follow it exactly**), `docs/modelling/abstention-policy.md`, `docs/operations/configuration.md` §3.7, §4, `docs/testing/test-fixtures.md` §7 |
| **Done when** | Pipeline tests pass and the abstain rate is reported |

---

## 1. Goal

One function, `claimsense.pipeline.predict(facts)`, that joins every earlier component and that the app, report and tests all call. This is the main **integration point** of the project, so this PR's e2e test runs `predict()` on artefacts produced by the real chain.

## 2. Files to add

| File | Contents |
|---|---|
| `src/claimsense/errors.py` | `ArtifactMismatchError`, `ArtifactNotFoundError`, `ExplainerUnavailableError` (move the latter here if defined earlier; keep an import alias) |
| `src/claimsense/topic.py` | `TopicChecker`: keyword gate (`topic.health_terms`, `claim_terms`) + small classifier (`models/topic_clf.pkl`) trained on in-scope facts vs off-topic negatives; threshold chosen so ≥ `in_scope_pass_rate` of val in-scope facts pass; `python -m claimsense.topic fit` |
| `src/claimsense/pipeline.py` | `load(artifacts_dir=None, *, classifier=None, calibrator=None, index=None, encoder=None, explainer=None, nli=None, topic=None)` — cached; real components by default, injectable for tests; checks `meta.json` / `calibrator_meta.json` / `index_meta.json` / `thresholds.json` / `config.yaml` agree → else `ArtifactMismatchError`; missing file → `ArtifactNotFoundError`. `predict(...)` exactly per the interface doc: validate → topic → (classify+calibrate ‖ retrieve) → gate → explain → cite-check; abstain codes and precedence per §3; explainer only called when no abstain; `latency_ms`; never writes to disk or logs facts |
| `src/claimsense/models/thresholds.py` | `fit_abstain_threshold(val_probs, y)` per `abstention-policy.md` §3 (target selective accuracy / coverage, floor) → updates `models/thresholds.json` + reports the curve |
| `tests/stubs/stub_classifier.py` | Logits from `tests/fixtures/models/stub_classifier.json` |
| `tests/fixtures/pipeline/queries.yaml`, `tests/fixtures/models/{stub_classifier.json,thresholds.json,meta.json,meta_mismatch.json}` | Per `test-fixtures.md` §7 |
| Tests | `tests/pipeline/test_predict_schema.py`, `test_off_topic.py`, `test_no_future_precedents.py`, `test_errors.py`, `test_cpu_only.py`, `tests/unit/test_abstain_codes.py`, `tests/unit/test_thresholds_fit.py`, `tests/unit/test_thresholds_mismatch.py`, `tests/bench/bench_latency.py` |

## 3. Files to modify

`config.yaml` (`input`, `topic`, `abstain`), `config.py` (`ArtifactMismatchError` on config ↔ `thresholds.json` mismatch), `src/claimsense/evaluate/report.py` (abstain rate per code on test, coverage-vs-selective-accuracy curve; uses `predict(..., explain=False, query_date=decision_date, exclude_doc_id=doc_id)`), `Makefile` (`bench`, `topic`, `thresholds`), `CHANGELOG.md`.

## 4. Tests to write

- **`test_predict_schema.py`**: every field rule in interface §2 on all confident queries (`probability == class_probabilities[label]`, sum to 1 ± 1e-6, cites ⊆ precedents, versions filled).
- **`test_abstain_codes.py`**: each code fires on its fixture group; precedence (short **and** off-topic → `INPUT_TOO_SHORT`); `LOW_CONFIDENCE` hides label/probability but keeps precedents; **explainer not called** for any abstain (spy).
- **`test_off_topic.py`**: motor, recipe, general question → `OFF_TOPIC`.
- **`test_no_future_precedents.py`**: with a fixed `query_date`, every precedent is earlier; `query_date` in the future → `ValueError`.
- **`test_errors.py`**: bad types/k → `TypeError`/`ValueError`; `meta_mismatch.json` → `ArtifactMismatchError`; missing calibrator → `ArtifactNotFoundError`; explainer raising → `ExplainerUnavailableError` propagated (app handles it in PR 17).
- **`test_cpu_only.py`**: `CUDA_VISIBLE_DEVICES=""` and `torch.cuda.is_available` patched False → still works.
- **`test_thresholds_fit.py`**: known toy curve → expected threshold; never below floor.
- **`bench_latency.py`** (not collected): 20 queries after warm-up, prints median/max, exits non-zero if any > 10 s.

## 5. E2E tests — the full chain

`stages.py`: `run_pipeline_artifacts(world)` = finetune(smoke) + calibrate + index + topic fit + thresholds fit, all on the world; `world_predict()` = `pipeline.load()` with **real** classifier/calibrator/index/topic from the world, hashing encoder, corpus-aware stub LLM, overlap stub NLI.

**`tests/e2e/test_e2e_16_pipeline.py`**:
- `pipeline.load()` from the world's artefacts succeeds (versions all consistent) — the first time every artefact is loaded **together**.
- For every world test record: `predict(facts_text, query_date=decision_date, exclude_doc_id=doc_id)` returns a schema-valid result; precedents all earlier; explanation cites ⊆ precedents.
- Off-topic and too-short queries abstain with the right codes against the real (not stub) topic checker.
- Changing `abstain.threshold` in config without refitting → `ArtifactMismatchError` (config ↔ artefact link holds end to end).
- Rebuild the dataset with a changed **V** key → `pipeline.load()` raises `ArtifactMismatchError` until adapter/calibrator/index are rebuilt (stale-artefact protection).
- The abstain-rate section appears in the world report.
- No socket opened; `CUDA_VISIBLE_DEVICES=""`.
- Contracts extended: `thresholds.json` ↔ config.

## 6. Definition of done

`make pr-check` → ALL CHECKS PASSED; run `slow.yml` on the branch, paste link; raise the floor.

## 7. Manual checks (Diya)

- [ ] Real artefacts: `make topic thresholds`; commit `models/thresholds.json` + config values with evidence in the PR.
- [ ] `CUDA_VISIBLE_DEVICES="" make bench` → paste median and max (each ≤ 10 s).
- [ ] In `uv run python`: try the example from `pipeline-interface.md` §7, and "my car was damaged in a flood" → `OFF_TOPIC`.
- [ ] `make report` → abstain rate per code on test.
