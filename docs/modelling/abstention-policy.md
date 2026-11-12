# ClaimSense — Abstention Policy

> When ClaimSense refuses to give an estimate, and how each refusal threshold is chosen: the calibrated-confidence threshold, the topic check, the precedent floor, and the coverage-versus-accuracy trade-off that decides how often the system says "we can't tell".

**Author:** Diya Shrivastava · **Owning PR:** 16 · **Status:** Planned

**Related:** FR-17, design decision D8, risks R12, R13, `calibration.md`, `retrieval-design.md` §4, `../architecture/pipeline-interface.md` §3–§4 (codes, order, messages).

---

## 1. Principle

A wrong answer given with confidence about a medical bill is worse than no answer (D8). ClaimSense therefore abstains when the case is outside what it learned, when it has nothing to compare with, or when similar cases went different ways.

Abstaining is not free: every refusal is a person who got no estimate. This document sets the thresholds so that trade-off is chosen deliberately, on validation data, and reported.

---

## 2. The five codes

Defined in `pipeline-interface.md` §3 and checked in this order; the first that fires is returned.

| Order | Code | Decided by | Threshold source |
|---|---|---|---|
| 1 | `INPUT_TOO_SHORT` | Character count | `input.min_chars` (fixed: 80) |
| 1 | `UNSUPPORTED_LANGUAGE` | Language detector | Fixed rule (English only) |
| 2 | `OFF_TOPIC` | Topic check (§5) | Tuned on val + off-topic fixtures |
| 4 | `NO_PRECEDENTS` | Retrieval floor | `retrieve.min_k`, `retrieve.min_similarity` (`retrieval-design.md` §4) |
| 5 | `LOW_CONFIDENCE` | Calibrated top-class probability (§3) | `abstain.threshold`, tuned on val |

This document owns how the thresholds for `OFF_TOPIC` and `LOW_CONFIDENCE` are set, and how all five are reported.

---

## 3. Confidence threshold (`LOW_CONFIDENCE`)

### Score

`confidence` = the highest of the three **calibrated** class probabilities. It is only meaningful after calibration (`calibration.md`).

### Data

Cross-fitted calibrated probabilities on `val` (`calibration.md` §3), so the threshold is not chosen on in-sample calibrated scores. Test is never used.

### Definitions

For a threshold τ, the system answers when `confidence ≥ τ`:

| Quantity | Definition |
|---|---|
| **Coverage(τ)** | Share of val queries answered |
| **Selective accuracy(τ)** | Accuracy on the answered queries |
| Selective macro-F1(τ) | Macro-F1 on the answered queries |

### Selection rule (fixed before PR 16 runs)

1. Consider τ from 0.40 to 0.90 in steps of 0.01.
2. Floor: τ ≥ **0.50**. With three classes, below 0.5 the top class may not be more likely than the other two combined; ClaimSense should not state an outcome it does not consider more likely than not.
3. Choose the **lowest** τ with **selective accuracy ≥ 0.75** and **coverage ≥ 0.50**.
4. If no τ meets both, choose the τ that gives coverage 0.50, and report that the accuracy target was not reached at that coverage.
5. Write the chosen τ, its val coverage and its val selective accuracy to `models/thresholds.json`, and to `abstain.threshold` in `config.yaml` (replacing the starting value 0.55).

The targets (0.75 accuracy, 0.50 coverage) are set now, before any val result exists. If early results show they are badly placed, they may be changed **once**, in the PR 16 description, with the reason, before test is run.

### `models/thresholds.json`

```json
{
  "abstain_threshold": 0.0,
  "chosen_on": "val_crossfit",
  "val_coverage": 0.0,
  "val_selective_accuracy": 0.0,
  "rule": "lowest tau >= 0.50 with selective_accuracy >= 0.75 and coverage >= 0.50",
  "topic_threshold": 0.0,
  "retrieve_min_similarity": 0.0,
  "retrieve_min_k": 2,
  "model_run_id": "…",
  "dataset_version": "v________"
}
```

---

## 4. Coverage–accuracy curve

The central figure for this policy, produced on val (for choosing) and on test (for reporting, PR 14/16).

| Element | Spec |
|---|---|
| X-axis | Coverage (0–1) |
| Y-axis | Selective accuracy (and selective macro-F1 as a second line) |
| Marker | The chosen operating point, labelled with τ |
| Reference | Horizontal line at full-coverage accuracy |
| Panels | All sources; India only (R13) |
| Summary number | **AURC** (area under the risk–coverage curve, risk = 1 − selective accuracy); lower is better |

Files: `reports/figures/coverage_accuracy_val.png`, `reports/figures/coverage_accuracy_test.png`.

### Reading the trade-off

| Move τ up | Move τ down |
|---|---|
| Fewer answers, each more reliable | More answers, more of them wrong |
| More users see "similar cases went different ways" | More users see a confident number that may be wrong |
| Safer for R12 (users treating output as advice) | More useful for users with common, clear-cut disputes |

---

## 5. Topic check (`OFF_TOPIC`)

Method `keyword_and_classifier`: two stages, both must pass.

### Stage A — keyword gate (cheap, catches obvious cases)

The input passes if it contains at least one term from **each** list (case-insensitive, stems allowed). Lists live in `config.yaml`.

| List | Examples |
|---|---|
| Health / treatment | hospital, admitted, admission, surgery, treatment, diagnosis, doctor, discharge, mediclaim, cashless, day care, OPD |
| Claim / insurance | claim, policy, insurer, insurance, TPA, repudiat*, reject*, denied, declined, reimburse*, settle* |

### Stage B — classifier (catches look-alikes)

- **Features:** the query embedding from the retrieval encoder (already computed, so no extra model).
- **Model:** logistic regression, in-scope vs off-topic.
- **In-scope examples:** `train` `facts_text`.
- **Off-topic examples (hand-built, committed as `tests/fixtures/off_topic.jsonl`):** about 200 short texts, including motor and home insurance claims, life-insurance claims, travel claims for lost baggage or cancellations, insurance questions that are not disputes ("which policy should I buy?"), medical questions with no claim, and unrelated text. Written by hand from general knowledge; never copied from decisions.
- **Threshold:** set so that **≥ 99% of val in-scope facts pass** (false refusals ≤ 1%). Recorded as `topic_threshold`.
- **Off-topic recall** on a held-out 30% of the fixture set: target **≥ 95%**, reported.

### Scope edge cases

| Input | In scope? |
|---|---|
| Overseas / travel **medical** treatment claim | ✅ (overseas mediclaim is a source product) |
| Personal-accident claim for **hospital costs** | ✅ |
| Personal-accident lump sum for disability | ❌ (`OFF_TOPIC`) |
| Critical-illness lump sum | ❌ in v1; noted in the scope backlog |
| Delay or interest complaint with the claim already paid | ❌ (excluded in `labelling-guide.md`) |

---

## 6. `NO_PRECEDENTS`

Fires when fewer than `retrieve.min_k` earlier decisions have cosine similarity ≥ `retrieve.min_similarity`. The floor is the 5th percentile of top-1 similarity on val (`retrieval-design.md` §4), so roughly 5% of in-scope val queries would be refused here. It catches inputs that pass the topic check but describe situations the dataset barely covers.

---

## 7. What the user sees

From `pipeline-interface.md` §2:

- **`LOW_CONFIDENCE`:** no outcome or probability; the similar past cases **are** shown, labelled "Similar past cases", with the message that similar cases went different ways. The user still gets evidence, just no number.
- **Every other code:** only the code-specific message and the disclaimer.
- No abstention calls the LLM, so refusals cost nothing.

---

## 8. Reporting (PR 16, shown on the Model Card page)

On the **test** split, with 95% bootstrap CIs:

| Quantity | All | India | UK | Ireland |
|---|---|---|---|---|
| Coverage at chosen τ | | | | |
| Selective accuracy | | | | |
| Selective macro-F1 | | | | |
| Full-coverage accuracy (no abstention) | | | | |
| Abstain rate: `OFF_TOPIC` | | | | |
| Abstain rate: `NO_PRECEDENTS` | | | | |
| Abstain rate: `LOW_CONFIDENCE` | | | | |
| Off-topic recall (fixtures) | | — | — | — |

If India's coverage is far below the other sources, that is reported as a jurisdiction finding (R13), not fixed by a separate Indian threshold in v1.

---

## 9. Change control

- Thresholds are fitted to one model run and one dataset version; `thresholds.json` records both, and `predict()` refuses a mismatch.
- Retraining or recalibrating the classifier means re-running §3 and §5 and regenerating the report.
- Any change to the selection rule is a new row in the experiment log with the reason.

---

## 10. Tests

| Test | Checks |
|---|---|
| `test_abstain_codes.py` | Each code fires on its fixture; precedence order holds (FR-17) |
| `test_off_topic.py` | Motor claim, recipe, general question → `OFF_TOPIC` (FR-17b) |
| `test_in_scope_fixtures_pass` | 20 hand-written in-scope descriptions pass the topic check |
| `test_threshold_rule` | On a synthetic coverage–accuracy curve the selection function returns the expected τ, including the fallback case |
| `test_threshold_floor` | τ is never below 0.50 |
| `test_low_confidence_shows_precedents` | `LOW_CONFIDENCE` result has `label is None` and non-empty `precedents` |
| `test_thresholds_mismatch` | `thresholds.json` from another run raises `ArtifactMismatchError` |
