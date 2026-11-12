# ClaimSense — Error Analysis and Fairness

> Why ClaimSense gets test cases wrong, who those errors fall on, and how far its explanations can be trusted. Written from 50 coded misclassifications, the slice metrics and the A6 audit. Nothing here changes the v1 model: findings go to `limitations.md`, the model card and `backlog-v2.md`.

**Author:** Diya Shrivastava · **Owning PR:** 15 (`eval/errors-fairness`) · **Status:** Draft / Final
**Related:** `error-taxonomy.md`, `fairness-analysis-plan.md`, `faithfulness-rubric.md`, `evaluation-protocol.md` §3, §8, §9, `reports/evaluation-report.md`, `responsible-ai/limitations.md`, `planning/backlog-v2.md`
**Coding sheet:** `reports/audits/ERR-____-__-__.csv` · **Slice output:** `reports/fairness/`

---

## 0. Run details

| Item | Value |
|---|---|
| Dataset version | `v________` |
| Model under test | `________` (run ID `________`) |
| Taxonomy committed before reading cases? | ☐ yes, commit `________` on ____-__-__ |
| Draw command | `python -m claimsense.audit draw ERR --seed 2026` |
| Population | Test, abstention on, not abstained, predicted ≠ true: **N = ____** errors |
| Sample size | 50 (or all ____ if fewer) |
| Coding dates | first pass ____ · re-code ____ (≥ 7 days later) |

---

## 1. Summary (fill last)

Three to five sentences a reviewer could read alone. Lead with the most harmful pattern.

> ______________________

| Key number | Value |
|---|---|
| Share of errors where the answer was **not in the facts** (I-codes) | __% |
| Share that are **model** errors (M-codes) | __% |
| Estimated label-noise rate among errors (D1) | __% |
| Slice flags raised | __ (FD-rate flags: __) |
| Explanation supported share (E7b) | 0.___ |

---

## 2. Sample counts

| Stratum | Minimum | Drawn | Note |
|---|---|---|---|
| False discouragement (true pay → pred `rejected`) | 12 | | |
| False hope (true `rejected` → pred pay) | 12 | | |
| Partial boundary (upheld ↔ partial) | 8 | | |
| High-confidence (P ≥ 0.80, overlapping) | 8 | | |
| India (overlapping) | 25 if available | | |
| Proportional remainder | — | | |
| **Total** | 50 | | |

---

## 3. Tallies

### 3.1 By letter (primary code)

| Letter | Meaning | All (n=50) | India (n=__) |
|---|---|---|---|
| D | Data / pipeline | __ (__%) | |
| I | Information not available | | |
| M | Model | | |
| C | Confidence (primary only if nothing else fits) | | |
| X | Cannot tell | | |

### 3.2 By code

| Code | Name | Primary | Secondary | India primary |
|---|---|---|---|---|
| D1 | Label error | | | |
| D2 | Segmentation fault | | | |
| D3 | Truncation loss | | | |
| D4 | Anonymisation damage | | | |
| D5 | OCR / parsing noise | | | |
| I1 | Decided on records not in facts | | | |
| I2 | Discretion / ex-gratia | | | |
| I3 | Procedural outcome | | | |
| I4 | New evidence at hearing | | | |
| M1 | Reason shortcut | | | |
| M2 | Partial boundary | | | |
| M3 | Jurisdiction confusion | | | |
| M4 | Rare pattern | | | |
| M5 | Temporal drift | | | |
| M6 | Language misread | | | |
| C1 | Should have abstained | | | |
| C2 | Near the boundary | | | |
| X1 | Cannot tell | | | |

Figure: `reports/figures/errors/code_tally.png`

### 3.3 Primary code × stratum

| Code | False discouragement | False hope | Partial boundary | High-confidence |
|---|---|---|---|---|
| D_ | | | | |
| I_ | | | | |
| M_ | | | | |
| X1 | | | | |

**Reading:** ______________________ (which codes drive the most harmful error, false discouragement?)

### 3.4 Label noise (D1)

D1 cases: __ of 50 → estimated label-noise rate among errors __% [CI __–__].
Caveat: the denominator is **errors**, not all test records, so this is not the dataset's overall noise rate.
Systematic pattern? ☐ no ☐ yes → bug filed: ____

### 3.5 Bugs found

| Bug | Code | Fix PR / commit | Regression test | Logged test re-load |
|---|---|---|---|---|
| | | | | |

(Only pipeline bugs are fixed in v1. Modelling ideas go to §7.)

---

## 4. Case vignettes

Three to five short, anonymised cases, one per major code, **in your own words**. No names, dates of birth, policy numbers or quoted passages.

### 4.1 [Code] — [one-line title]

| Field | Value |
|---|---|
| Country / insurer type / rejection reason | |
| True → predicted (P) | |
| Stratum | |

**What happened:** ______________________
**Why the model erred:** ______________________
**What it tells us:** ______________________

### 4.2 [Code] — [one-line title]

…

### 4.3 [Code] — [one-line title]

…

---

## 5. Fairness by slice

From `reports/fairness/slices.csv` (test, model under test). Metrics only where n ≥ 30; ECE only where n ≥ 100. Exploratory: no multiple-comparison correction.

### 5.1 Summary table

| Slice | Value | n | Macro-F1 [CI] | FD rate [CI] | FH rate [CI] | Pred vs obs P(pay) | ECE / Brier | Abstain | Flag |
|---|---|---|---|---|---|---|---|---|---|
| country | IN | | | | | | | | |
| country | GB | | | | | | | | |
| country | IE | | | | | | | | |
| insurer (IN) | public | | | | | | | | |
| insurer (IN) | private | | | | | | | | |
| insurer (IN) | standalone_health | | | | | | | | |
| claim band | lt_50k | | | | | | | | |
| claim band | 50k_2l | | | | | | | | |
| claim band | 2l_5l | | | | | | | | |
| claim band | gt_5l | | | | | | | | |
| claim band | unknown | | | | | | | | |
| tercile | small | | | | | | | | |
| tercile | medium | | | | | | | | |
| tercile | large | | | | | | | | |

Intersections (only where both values have n ≥ 30): country × tercile, India insurer type × claim band → `reports/fairness/slices.csv`.

### 5.2 Flags

| Rule | Threshold | Fired on | Evidence |
|---|---|---|---|
| 1. Macro-F1 gap | > 0.10, CIs do not overlap | | |
| 2. FD-rate ratio | > 1.5, CI of difference excludes 0 | | |
| 3. ECE | > 0.10 (n ≥ 100) | | |
| 4. Abstain-rate ratio | > 2.0 | | |

### 5.3 Write-up per flagged slice

Copy this block for each flag. FD-rate flags first.

**Slice:** ____ = ____ vs ____
**Finding in plain words:** ______________________
**Which explanation does the evidence support?**

| Check | Result | Points to |
|---|---|---|
| Base rates (train / test) | | world differs / model |
| Calibration-in-the-large (pred vs obs P(pay)) | | |
| Same gap for B3? | | |

**Conclusion:** ☐ data is harder for this slice ☐ model treats it worse ☐ cannot tell
**Error codes most common in this slice (from §3):** ______________________
**Actions:** limitations line ☐ · model card row marked ☐ · app note text: "______________________" ☐ · backlog item ☐

---

## 6. Explanation faithfulness

From `reports/audits/A6-summary.json` (40 test queries, seed 2025). Full numbers are in `evaluation-report.md` §6; this section reads them.

| Metric | Value [CI] | Target |
|---|---|---|
| Supported share, kept (E7b) | | ≥ 0.90 |
| Checker agreement, pooled (E7c) | | ≥ 0.90 |
| False-drop rate | | — |
| Advice / guarantee count | | 0 |

### 6.1 Explanation-failure tally (`error-taxonomy.md` §6)

Source: `reports/explanations/dropped.jsonl`, `reports/audits/A6-disagreements.csv`

| Code | Name | Count |
|---|---|---|
| E1 | Invented detail | |
| E2 | Unsupported claim | |
| E3 | Misattribution | |
| E4 | Overgeneralisation | |
| E5 | Contradicts predicted label | |
| E6 | Checker false drop | |
| E7 | Checker false keep | |

**Reading:** ______________________ (is the checker too strict, too loose, or is the prompt inventing detail?)

### 6.2 Reviewer consistency (A6)

Re-scored 20 sentences blind after ≥ 7 days: agreement __% · κ = ____ (κ < 0.6 → noted as a limitation)

---

## 7. Actions

Every code with ≥ 3 primary cases, and every slice flag, maps to at least one line here.

| Source (code / flag) | Count | Goes to | Text or item |
|---|---|---|---|
| | | `limitations.md` | |
| | | `MODEL_CARD.md` | |
| | | Streamlit note | |
| | | `backlog-v2.md` | |

### Reading the overall pattern

| Pattern | Seen? | What it suggests |
|---|---|---|
| I-codes dominate | ☐ | The ceiling is what users can tell us; better models will not help much |
| M1 dominates | ☐ | The model leans on the rejection reason; the gap over B2 is smaller than it looks |
| M5 concentrated in recent quarters | ☐ | Retraining cadence matters (ties to the drift check) |
| C1 large | ☐ | Abstention is too permissive for high-confidence errors |
| X1 large | ☐ | The errors are not well understood; say so plainly |

---

## 8. Reviewer consistency (error coding)

| Item | Value |
|---|---|
| Cases re-coded blind | 10 |
| Gap since first coding | __ days (≥ 7) |
| Agreement on primary letter | __ / 10 · κ = ____ |
| Agreement on full code | __ / 10 |
| Disagreements | listed below; the **first** coding stays in the tallies |

| doc_id | First code | Second code | Note |
|---|---|---|---|
| | | | |

---

## Done-when check (PR 15)

- [ ] 50 cases (or all) coded in `reports/audits/ERR-<date>.csv`
- [ ] Failure modes written up **with counts** (§3)
- [ ] Performance by insurer type and claim size reported (§5)
- [ ] Faithfulness on the 40-case set read and tallied (§6)
- [ ] Every code with ≥ 3 cases and every flag mapped to an action (§7)
- [ ] No v1 model, threshold or prompt changed on the basis of test results
