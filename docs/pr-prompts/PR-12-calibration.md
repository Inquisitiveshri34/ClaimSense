# PR 12 · Calibration

| | |
|---|---|
| **Branch** | `feat/calibration` |
| **Depends on** | PR 11 |
| **Covers** | FR-12, NFR-03 |
| **Read first** | `docs/modelling/calibration.md` (all, esp. §4 method rule), `docs/evaluation/evaluation-protocol.md`, `docs/operations/configuration.md` §3.6, §4 |
| **Done when** | Test ECE ≤ 0.05 for the real fine-tuned model |

---

## 1. Goal

Make the probability honest: a "70%" should be right about 70% of the time. Fit on **val only**; touch test once to report.

## 2. Files to add

| File | Contents |
|---|---|
| `src/claimsense/models/calibrate.py` | `TemperatureScaler`, `IsotonicCalibrator` (one-vs-rest + renormalise); `Calibrator` facade with `fit(logits, y)`, `transform(logits) -> probs`, `save/load` (`models_dir()/calibrator.pkl` + `calibrator_meta.json` with method, temperature, `model_run_id`, `dataset_version`, `fit_split: "val"`); method choice per `calibration.md` §4 (isotonic only if val ≥ `isotonic_min_val` and cross-fit gain ≥ `isotonic_min_gain`); 5-fold cross-fit on val for honest val numbers |
| `src/claimsense/models/calib_metrics.py` | `ece(probs, y, bins)` (top-label, equal-width), classwise ECE, Brier (multiclass), reliability-diagram data |
| `src/claimsense/models/calibrate_cli.py` (or `__main__` subcommand) | `python -m claimsense.models calibrate`: load adapter → val logits → fit → val/test ECE + Brier before/after → MLflow → figures `reports_dir()/figures/reliability_{val,test}.png` |
| `tests/fixtures/models/calibrator_tiny.pkl` | Known temperature |
| `tests/unit/test_calibration_math.py`, `tests/unit/test_calibrator.py` | See §4 |

## 3. Files to modify

`config.yaml` (`calibrate`; **M**), `config.py`, `tests/leak/test_temporal_split.py` (new case: a calibrator whose meta says `fit_split != "val"` or that was fitted on rows whose ids are in test → FAIL), `Makefile` (`calibrate`), `CHANGELOG.md`.

## 4. Tests to write

- **`test_calibration_math.py`**: ECE of perfectly calibrated synthetic data ≈ 0; ECE of a hand-built 2-bin example equals the hand value; Brier known value; temperature 1.0 is identity; softmax rows sum to 1.
- **`test_calibrator.py`**: temperature scaling lowers ECE on deliberately over-confident logits; the method rule picks temperature when val is small; save → load → identical outputs; meta links to `model_run_id` and `dataset_version`; loading with a mismatched adapter run id raises `ArtifactMismatchError`.

## 5. E2E tests

`stages.py`: `run_calibrate(world)` (→ `run_finetune`).

**`tests/e2e/test_e2e_12_calibration.py`**:
- Calibrator fitted on world val from the smoke model's logits; `calibrator_meta.json` links to the smoke adapter's `run_id` and to `LATEST`.
- `fit_split == "val"`; no test `doc_id` appears in the fit set.
- World val ECE after calibration ≤ ECE before (cross-fit numbers).
- Reliability figures written in the world reports dir.
- Contracts extended: adapter ↔ calibrator ↔ dataset versions agree.

## 6. Definition of done

`make pr-check` → ALL CHECKS PASSED; raise the floor.

## 7. Manual checks (Diya)

- [ ] `make calibrate` with the real adapter. Paste val/test ECE and Brier before/after with run IDs. **Gate: test ECE ≤ 0.05.**
- [ ] Look at `reliability_test.png`: points near the diagonal.
