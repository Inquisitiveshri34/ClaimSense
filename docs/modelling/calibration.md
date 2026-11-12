# ClaimSense — Calibration

> How ClaimSense makes its probabilities mean what they say: which calibration method is used and how it is chosen, which data it is fitted on, how ECE and Brier score are computed, what the reliability diagram shows, and what happens if the ECE gate is missed.

**Author:** Diya Shrivastava · **Owning PR:** 12 · **Status:** Planned

**Related:** FR-12, NFR-03, design decision D5, `finetuning-spec.md` §8, `abstention-policy.md`, `../architecture/leakage-contract.md` (L3), `../architecture/pipeline-interface.md` §2.

---

## 1. Why calibrate

A user reads "about 7 in 10 similar cases were upheld" and decides whether to fight a claim. That sentence is only honest if, among all cases where ClaimSense says 70%, about 70% really were upheld. Fine-tuned networks are usually **over-confident**, so raw softmax scores are not usable as stated probabilities (D5).

Calibration also feeds abstention: the confidence threshold in `abstention-policy.md` is only meaningful on calibrated scores.

---

## 2. What is calibrated

| Item | Value |
|---|---|
| Model | The shipped classifier (`models/lora-adapter/`, or the strongest baseline if R8 applied) |
| Input to the calibrator | Raw logits for 3 classes, label order from `meta.json` `id2label` |
| Output | 3 class probabilities summing to 1 |
| Derived | P(any payment) = P(upheld) + P(partially upheld) |

---

## 3. Fit set and the val problem

### The rule

The calibrator is fitted on the **`val` split only** (FR-12). The `test` split is never used for fitting or choosing anything (L3); a test asserts this.

### The problem

`val` is also used for early stopping and hyperparameter selection (PR 11) and for the abstain threshold (PR 16). Reusing it for calibration makes **val** calibration numbers look better than they are.

### How it is handled

| Purpose | Data |
|---|---|
| Choosing between methods (§4) | **5-fold cross-fitting on val:** fit on 4 folds, score on the 5th, repeat; folds stratified by label and source |
| Fitting the shipped calibrator | All of `val` |
| Choosing the abstain threshold | Cross-fitted val probabilities from the same 5 folds (so the threshold is not chosen on in-sample calibrated scores) |
| The gate | **Test** ECE, which no step has touched |

**Optional, if val has at least 600 records:** split val by date into val-A (Jan–Jun 2024: early stopping, model selection) and val-B (Jul–Dec 2024: calibration, threshold). This is a sub-split inside `val`, so it does not change the dataset hash. Decide at PR 11 when the val size is known and record the choice in the experiment log.

---

## 4. Methods

| Method | How it works | Changes the predicted label? | Data needed | Risk |
|---|---|---|---|---|
| **Temperature scaling** | Divide all logits by one number *T* fitted to minimise negative log-likelihood | **No** (arg-max is unchanged, so macro-F1 is unchanged) | Small (one parameter) | Cannot fix class-specific miscalibration |
| **Isotonic, one-vs-rest** | A monotone step function per class on its probability, then renormalise to sum to 1 | Can | Large (many hundreds of records per class) | Overfits small val sets; renormalisation can distort |

### Fitting details

- **Temperature:** minimise NLL over *T* in [0.05, 20] with L-BFGS on log *T*; record *T*. *T* > 1 means the model was over-confident.
- **Isotonic:** `sklearn.isotonic.IsotonicRegression(out_of_bounds="clip")` per class on softmax outputs, then divide by the row sum.

### Selection rule (fixed before PR 12 runs)

Use **temperature scaling** unless **both** hold:

1. isotonic lowers cross-fitted val top-label ECE by at least **0.01**, and
2. `val` has at least **1,000** records.

Temperature is the default because it keeps the classifier's decisions identical and has almost no variance. The rule is written down now so the choice cannot be made by looking at test.

---

## 5. Metrics

All computed by `claimsense.eval.calibration`, with 95% bootstrap CIs (1,000 resamples).

### Top-label ECE (the gated number)

Split predictions into *M* = 15 equal-width bins by confidence (the top class probability). For each bin *b* with *n_b* predictions:

```text
ECE = Σ_b (n_b / N) · | accuracy(b) − mean_confidence(b) |
```

**Gate (NFR-03):** test top-label ECE ≤ **0.05**.

### Also reported

| Metric | What it adds |
|---|---|
| Adaptive ECE (15 equal-count bins) | Less sensitive to empty high-confidence bins |
| Class-wise ECE | Average ECE of each class's probability, so a badly calibrated `partially_upheld` cannot hide |
| Binary ECE, any payment | Calibration of the number the app also shows |
| **Brier score** (multiclass) | Σ over classes of (p − y)², averaged over records; range 0–2, lower is better. Rewards both calibration and sharpness |
| NLL | Log-loss; what temperature scaling optimises |

### Small-sample warning

ECE is biased upward on small sets: even a perfectly calibrated model shows ECE > 0 because bins are noisy. To show how much of the measured ECE is noise:

1. Take the test confidences as given.
2. Simulate labels as if the model were perfectly calibrated (draw each outcome with its predicted probability), 1,000 times.
3. Report the median ECE of these simulations as the **noise floor** next to the real ECE.

If the noise floor itself is near 0.05 (likely if test has only a few hundred records), say so in the report; the gate is then judged together with the CI and the reliability diagram, not on the point estimate alone.

---

## 6. Reliability diagram

| Element | Spec |
|---|---|
| X-axis | Mean confidence per bin (0–1) |
| Y-axis | Observed accuracy per bin |
| Marks | Dots per bin, sized or annotated by count; gap to the diagonal shaded |
| Reference | Diagonal *y = x* (perfect calibration) |
| Under the plot | Histogram of predictions per bin, so empty bins are visible |
| Panels | Before vs after calibration; val (cross-fitted) and test |
| Extra panels | Per source (India, UK, Ireland), and the binary any-payment view |

Files:

```text
reports/figures/reliability_val_before_after.png
reports/figures/reliability_test.png
reports/figures/reliability_test_by_source.png
reports/figures/reliability_test_any_payment.png
```

The test figure also appears on the app's Model Card page (FR-18).

---

## 7. Artefact

`models/calibrator.pkl` holds a `Calibrator` object:

```python
class Calibrator:
    method: Literal["temperature", "isotonic"]
    temperature: float | None
    isotonic: list[IsotonicRegression] | None
    id2label: dict[int, str]
    fit_n: int
    dataset_version: str
    model_run_id: str        # the classifier these logits came from

    def fit(self, logits: np.ndarray, y: np.ndarray) -> "Calibrator": ...
    def predict_proba(self, logits: np.ndarray) -> np.ndarray: ...
```

`predict()` refuses to load a calibrator whose `model_run_id` or `dataset_version` differs from the adapter's `meta.json` (`ArtifactMismatchError`).

---

## 8. If the gate fails

1. Check the reliability diagram: is the miss in one region (for example, high-confidence bins) or one source?
2. If one source dominates the error (likely India under R13), report per-source ECE and consider a source-specific temperature, logged as a new experiment row.
3. Try isotonic even if the selection rule did not pick it, and report both.
4. If the gate is still missed, **report it**, and change the app's wording from "about 7 in 10" to a coarser band ("more likely than not", "uncertain") until a fix lands. Do not move the test set or re-bin to pass.

---

## 9. Results (filled in by PR 12)

| Quantity | Before calibration | After calibration |
|---|---|---|
| Method chosen | — | |
| Temperature *T* | — | |
| Val top-label ECE (cross-fitted) [CI] | | |
| Test top-label ECE [CI] | | |
| Test ECE noise floor | — | |
| Test class-wise ECE | | |
| Test Brier | | |
| Test any-payment ECE | | |
| **Gate (test ECE ≤ 0.05)** | — | ☐ pass / ☐ fail |

---

## 10. Tests

| Test | Checks |
|---|---|
| `test_calibrator_fits_val_only` | Fitting code raises if given any record with `split == "test"` (L3) |
| `test_temperature_preserves_argmax` | Predicted labels identical before and after temperature scaling |
| `test_probabilities_sum_to_one` | Both methods, tolerance 1e-6 |
| `test_ece_known_values` | Hand-computed ECE on a small fixture matches the function |
| `test_calibrator_roundtrip` | Save → load gives identical probabilities |
| `test_calibrator_mismatch` | Mismatched run ID or dataset version raises `ArtifactMismatchError` |
