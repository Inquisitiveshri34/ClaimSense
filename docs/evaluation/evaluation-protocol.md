# ClaimSense — Evaluation Protocol

> The pre-registered plan for judging ClaimSense: every metric, target, comparison, slice and statistical rule, fixed and committed in PR 7, **before** EDA (PR 8) and before any model is scored on the test split. The evaluation report in PR 14 executes this file. Anything the report does that this file does not say is labelled a deviation (§12).

**Author:** Diya Shrivastava · **Owning PR:** 7 (written and frozen) → 13 (rubrics added) → 14 (executed) → 15 (slices and errors) · **Status:** Planned

**Related:** `../PRD.md` §4.1, FR-12, FR-16, FR-17, NFR-03, NFR-05, NFR-06, risks R3, R8, R12, `../architecture/leakage-contract.md` (L3), `../modelling/baselines.md` §5, `../modelling/calibration.md`, `../modelling/retrieval-design.md`, `../modelling/citation-checking.md`, `../modelling/abstention-policy.md`, `../data/manual-audit-protocol.md` (A5, A6), `retrieval-rubric.md`, `faithfulness-rubric.md`, `error-taxonomy.md`, `fairness-analysis-plan.md`.

---

## 1. Why this file exists

If metrics and targets are chosen after seeing results, any project can be made to look successful: pick the metric that came out best, drop the slice that looks bad, move the threshold until the number clears. Writing the plan down first is called **pre-registration**. It is what makes the PR 14 claim "beats every baseline" credible to a reviewer who was not there.

The promise in `05-project-description.md` §7 ("targets are set before seeing the data") is kept here.

---

## 2. Freeze rules

1. This file is committed in PR 7 and tagged `eval-protocol-v1`. Its SHA-256 is printed at the top of `reports/evaluation-report.md`.
2. After the tag, these **cannot change**: endpoints (§4), targets, statistical rules (§5), slice definitions (§8), audit sample sizes and seeds (§9), decision rules (§10).
3. Files added later **elaborate** this protocol but may not loosen it:

   | File | Written in | Constraint |
   |---|---|---|
   | `retrieval-rubric.md` | PR 13, before the A5 sample is drawn | Gate numbers come from §4 here |
   | `faithfulness-rubric.md` | PR 13, before the A6 sample is drawn | Gate numbers come from §4 here |
   | `error-taxonomy.md` | PR 15, before the 50 cases are read | Sample size and strata come from §9 here |
   | `fairness-analysis-plan.md` | PR 15, before slice numbers are computed | Slices and flag rules come from §8 here |

4. Any change after the tag goes in the deviations log (§12) with the date, what changed, why, and **whether it was made before or after seeing test numbers**. A post-test change is reported, never hidden.

---

## 3. Data and split discipline

| Split | Decision dates | Used for | Never used for |
|---|---|---|---|
| `train` | ≤ 2023-12-31 | Fitting models, building the precedent index | — |
| `val` | 2024 | Hyperparameters, seed choice, calibrator fit, abstain threshold, retrieval `k`, NLI threshold | Reported as the final result |
| `test` | ≥ 2025-01-01 | The PR 14 report, A5/A6 audits, PR 15 error and fairness analysis | Choosing **anything** |

### Test-split access (L3)

- Only `python -m claimsense.eval report` may load `test.parquet`. Any other loader raises (`test_baselines_no_test_split` and friends).
- Every load appends one line to `reports/test_access.log`: timestamp, git SHA, model run ID, purpose.
- **Planned loads:** one final report run per frozen model. A re-run is allowed only to fix a bug that does not change a modelling choice (a plotting error, a crash, a wrong file path). Each re-run is logged with the reason.
- Nothing seen in PR 14 or PR 15 feeds back into the v1 model. Ideas that come out of the test results go to `../planning/backlog-v2.md`.

### Expected test size

The 2025+ split is the smallest by construction (decisions are published with a lag). If test has **fewer than 150 records**, the report states this in its first paragraph, all CIs are shown, and no claim is made from a point estimate alone. The split is not changed to make test bigger (that would break L3).

---

## 4. Endpoints and targets

**Gate** = must pass for the v1.0 release criteria in `PRD.md` §4.3. **Reported** = must appear in the report with CIs; no pass/fail.

| ID | Question | Metric | Split | Target | Type |
|---|---|---|---|---|---|
| **E1** | Does fine-tuning beat simpler models? | Macro-F1, 3 classes, full coverage (§6) | test | Higher than each of B1–B5; 95% CI does not overlap B3's | **Gate** |
| E2 | How well does it rank "any payment"? | PR-AUC, score = P(upheld) + P(partially upheld), with base rate | test | Above B3 | Reported |
| E3 | Is `partially_upheld` ignored? | Per-class F1 | test | `partially_upheld` F1 > 0 and not below B3's | Reported, flagged if missed |
| **E4** | Do probabilities mean what they say? | ECE (definition in `calibration.md` §4), Brier, reliability diagram | test | **ECE ≤ 0.05** | **Gate** |
| E5 | Does abstaining help? | Coverage, selective macro-F1, risk–coverage curve, AURC | test | At the val-chosen operating point, selective macro-F1 ≥ full-coverage macro-F1 | Reported, sanity check |
| E6 | Are precedents on topic? | Reason match@5, topic match@5, hit@5, outcome agreement@5 (A5) | test (40) | Reason match@5 ≥ 0.60; hit@5 ≥ 0.85 | Reported |
| **E6a** | Is the earlier-only filter correct? | Share of returned precedents with `decision_date < query_date` | test (all) | **100%** | **Gate** |
| **E7a** | Does every shown sentence carry a valid cite? | Structural check, every test query | test (all) | **100%** | **Gate** |
| **E7b** | Are kept sentences really supported? | Supported share of kept sentences (A6) | test (40) | **≥ 0.90** | **Gate** |
| **E7c** | Does the NLI checker agree with a human? | Checker agreement, kept + dropped sample (A6) | test (40) | **≥ 0.90** | **Gate** |
| **E8** | Is it interactive? | p50 / p95 seconds per `predict()` on a laptop CPU, 50 test queries, first load excluded | test | **p95 ≤ 10 s** | **Gate** |
| E9 | Where does it fail? | Breakdowns in §8; India-only; facts-vs-findings gap; cross-country | test | Flag rules in §8 | Reported |

Targets for E6 are not gates because the classifier does not use retrieval; poor retrieval weakens the explanation, which E7 already gates.

---

## 5. Statistical rules

| Rule | Value |
|---|---|
| Confidence intervals | Percentile bootstrap, **1,000 resamples**, seed `13`, records resampled with replacement **stratified by `source`** |
| Same metric code everywhere | `claimsense.eval.metrics.score(y_true, proba)`; no model gets a friendlier metric |
| Headline comparison (E1 vs B3) | Pre-registered rule: 95% CIs do not overlap. This is conservative |
| Supporting comparison | **Paired** bootstrap of the macro-F1 difference (same resample indices for both models), 95% CI. Reported beside the headline; the headline conclusion is still drawn from the non-overlap rule |
| Fine-tuned model seeds | 3 seeds; report mean ± sd on val. The **shipped** seed is chosen on val, never test |
| Multiple comparisons | E1 is an intersection test ("beats each of five"), so no correction is needed for the gate. Slice results (§8) are **exploratory** and labelled so |
| Small slices | A metric is printed only for n ≥ 30. Below that, counts only. ECE only for n ≥ 100 (else Brier) |
| Audit samples (40 cases) | CIs by bootstrap over **queries**, not sentences or precedents (cluster bootstrap), because items within one query are correlated |
| Rounding | Metrics to 3 decimals, CIs to 2 |

---

## 6. Classification details

- **Input:** `facts_text` only (complaint + insurer position). Never `findings_text` or award text (L1).
- **Full coverage for E1–E4.** Abstention is **switched off** when computing E1–E4, so every model is scored on every test record and baselines (which never abstain) are compared fairly.
- **Selective metrics for E5.** Abstention switched on at the operating point stored in `models/thresholds.json`. Abstained records are excluded from selective metrics and counted in coverage.
- **Binary view.** `label_binary = label != "rejected"` ("any payment"). Used for E2 and for the harm rates in `fairness-analysis-plan.md`.
- **Model under test.** The adapter in `models/lora-adapter/` with the calibrator in `models/calibrator.pkl`. If R8 applied (fine-tuning lost on val), the strongest baseline is the model under test and the report says so on its first page.

---

## 7. Leakage and shift checks in the report

| Check | How | What it means |
|---|---|---|
| **Facts-vs-findings gap** | Fit B3 on `findings_text` (train), score on test; compare with B3 and the fine-tuned model on `facts_text` | Findings contain the answer, so this is a rough ceiling. If the facts model comes within 0.05 macro-F1 of it, treat it as a leakage alarm (R3) and check L1 probes before writing anything else |
| **Leak probes** | All `tests/leak/` pass on the evaluated dataset version | A failing probe blocks the report |
| **India-only** | All E1–E4 metrics on `country == IN` | India is the primary user base; it gets its own table, not a footnote |
| **Cross-country transfer** | Fit B3 and the fine-tuned model (one seed) on train **without** India; score on India test | How much Indian performance relies on Indian training data |
| **Temporal drift** | E1 on test by decision quarter | A downward trend across 2025 quarters suggests rules changed after the training window |

---

## 8. Slices and flag rules (fixed here)

| Slice | Values | Note |
|---|---|---|
| `country` | IN, GB, IE | Primary slice |
| `insurer_type` | public, private, standalone_health | Analysed **within India** (see `fairness-analysis-plan.md` §4) |
| `claim_amount_band` | lt_50k, 50k_2l, 2l_5l, gt_5l, unknown | Also within-country terciles |
| `rejection_reason` | 6 enum values | |
| `decision_year` / quarter | 2025 Q1 … | Drift |

**Flag rules.** A slice result is a **finding** that must be written up in `../responsible-ai/limitations.md` and the model card when any of these holds (both slice values with n ≥ 30):

1. Macro-F1 gap between the best and worst value > **0.10** and their 95% CIs do not overlap.
2. False-discouragement rate (true any-payment, predicted `rejected`) ratio worst/best > **1.5** and the bootstrap CI of the difference excludes 0.
3. ECE > **0.10** in any value with n ≥ 100.
4. Abstain-rate ratio worst/best > **2.0**.

---

## 9. Manual audits and samples

| Audit | n | Draw | Strata | Rubric |
|---|---|---|---|---|
| A5 Retrieval | 40 test queries (shared with A6) | `python -m claimsense.audit draw A5A6 --seed 2025` | India ≥ 20 if available; label-proportional within source; ≥ 5 true `partially_upheld` | `retrieval-rubric.md` |
| A6 Faithfulness | Same 40 queries; all kept sentences + up to 40 dropped | Same draw | As above | `faithfulness-rubric.md` |
| Error analysis | 50 misclassified, non-abstained test records | `--seed 2026` | By confusion cell (see `error-taxonomy.md` §2) | `error-taxonomy.md` |

The 40 queries are drawn from test records the model did **not** abstain on, because there is no explanation to audit otherwise. Abstained queries are reported separately as a count by code.

---

## 10. Decision rules if a target is missed

| Missed | Action | Never allowed |
|---|---|---|
| E1 | Report honestly with per-class analysis; ship the strongest model (R8) | Re-tuning on test; changing the primary metric |
| E4 | Report; add an ECE warning to the model card; v2 backlog item (isotonic or more val data) | Refitting the calibrator on test |
| E6a, E7a | Bug. Fix, add a regression test, re-run the report (logged load) | Shipping with the bug |
| E7b / E7c | Fix the checker or prompt on a **val** dev set; draw a **fresh** A6 sample (new seed); report both results | Re-scoring the same sample after the fix as the reported number |
| E8 | Reduce `explain.max_sentences`, then `retrieve.k`; re-measure | Excluding slow queries from the timing set |
| A flag in §8 | Write it up (limitations, model card, app note for that slice) | Dropping or merging the slice after seeing it |

---

## 11. Report outline (`reports/evaluation-report.md`)

1. Protocol hash, dataset version, model run ID, test size, test-access log summary
2. E1–E3 table: all models, macro-F1 [CI], per-class F1, PR-AUC (base rate), paired differences vs B3 and B5
3. Calibration: ECE, Brier, reliability diagram (val and test)
4. Abstention: coverage, selective metrics, risk–coverage curve, abstain counts by code
5. Retrieval: automatic proxies (all test) + A5 results
6. Explanations: structural check (all test) + A6 results
7. Latency: p50/p95
8. Leakage and shift checks (§7)
9. Slices (§8) — summary here, detail in `fairness-analysis-plan.md` output
10. Gate summary: every gate with pass/fail
11. Deviations (§12)

```text
src/claimsense/eval/report.py      # the only test-split loader
src/claimsense/eval/metrics.py     # score(), bootstrap_ci(), paired_diff_ci()
reports/evaluation-report.md       # generated
reports/figures/                   # reliability, risk–coverage, per-slice plots
reports/test_access.log
```

| Test | Checks |
|---|---|
| `test_protocol_hash_in_report` | Report header hash equals SHA-256 of this file at tag `eval-protocol-v1` |
| `test_only_report_loads_test` | Any other module loading `test.parquet` raises |
| `test_bootstrap_deterministic` | Same seed → identical CIs |
| `test_paired_uses_same_indices` | Paired difference uses one index array for both models |
| `test_small_slice_suppressed` | n < 30 slice prints counts only |
| `test_full_coverage_e1` | E1–E4 computed with abstention disabled |

---

## 12. Deviations log

| # | Date | What changed | Why | Before or after seeing test numbers |
|---|---|---|---|---|
| | | | | |
