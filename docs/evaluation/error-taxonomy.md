# ClaimSense — Error Taxonomy

> The categories used to explain why ClaimSense got 50 test cases wrong: how the 50 cases are chosen, the code list (data, missing information, model, confidence), the order in which codes are tried so two readings of one case agree, and how the tallies turn into limitations and v2 backlog items rather than v1 changes.

**Author:** Diya Shrivastava · **Owning PR:** 15 (written before the cases are read) · **Status:** Planned

**Related:** `evaluation-protocol.md` §3 (no feedback into v1), §9, `fairness-analysis-plan.md`, `faithfulness-rubric.md` §9, `../data/labelling-guide.md`, `../data/manual-audit-protocol.md` (A1–A3), `../architecture/leakage-contract.md`, `../modelling/finetuning-spec.md`, `../modelling/abstention-policy.md`, `../responsible-ai/limitations.md`, `../planning/backlog-v2.md`, `../../reports/error-analysis.md`.

---

## 1. Purpose and the rule that limits it

A macro-F1 number says how often the model is wrong; it does not say **why**. Error analysis sorts mistakes into causes so the limitations section is specific ("a third of errors were cases decided on documents the user never sees") instead of generic.

**The rule:** this analysis reads the **test** split. Nothing learned here changes the v1 model, its thresholds or its prompts (`evaluation-protocol.md` §3). Findings go to `limitations.md`, the model card and `backlog-v2.md`. Fixing v1 on test errors would make the test numbers optimistic.

The one exception is a **bug** (a pipeline error, not a modelling choice), which is fixed, regression-tested and re-reported with a logged test load.

---

## 2. Sample of 50

| Item | Value |
|---|---|
| Population | Test records, model under test, abstention **on**, not abstained, predicted label ≠ true label |
| Draw | `python -m claimsense.audit draw ERR --seed 2026` |
| If fewer than 50 errors exist | Take all, and say so |

### Strata (minimums, then proportional)

| Stratum | Definition | Minimum | Why |
|---|---|---|---|
| **False discouragement** | True `upheld` or `partially_upheld`, predicted `rejected` | 12 | The most harmful error: a person may give up a claim they would have won |
| **False hope** | True `rejected`, predicted `upheld` or `partially_upheld` | 12 | Wastes time and raises expectations |
| **Partial boundary** | `upheld` ↔ `partially_upheld` | 8 | Shows whether amount reasoning is the problem |
| **High-confidence** | Any of the above with calibrated P(predicted) ≥ 0.80 | 8 (overlapping) | These should have been caught by abstention |
| India | Any error with `country == IN` | 25 if available (overlapping) | Primary user base |

Fill minimums first, then the rest proportional to each confusion cell's share of all errors. Record the draw counts in the summary.

---

## 3. What is read for each case

1. `facts_text` (what the model saw) and `findings_text` + award (what decided the case)
2. True and predicted label, all three calibrated probabilities
3. The 5 precedents and the explanation, with A6 verdicts if the case is in that sample
4. Metadata: country, insurer type, claim band, rejection reason, product, decision date
5. Token count of `facts_text` and whether it was truncated
6. Train-set count of the case's `(rejection_reason, country)` cell

Budget about 4–5 minutes per case.

---

## 4. The codes

Each case gets **one primary code** (the cause that, if removed, would most likely have fixed the prediction) and **up to two secondary codes**.

### D — Data and pipeline (the dataset or preprocessing is at fault)

| Code | Name | Evidence test | Goes to |
|---|---|---|---|
| D1 | Label error | Reading the award, the gold label is wrong per `labelling-guide.md` | Bug if systematic; A2 rule fix in v2 |
| D2 | Segmentation fault | The insurer's position is missing from `facts_text`, or findings text leaked in (L1) | **Bug** (leak) or A1 fix |
| D3 | Truncation loss | The deciding fact sits in the part of `facts_text` cut by head-tail truncation | v2: longer context / chunking |
| D4 | Anonymisation damage | A mask removed decisive information (a date range, a hospital type, a sum insured) | v2: anonymiser allowlist |
| D5 | OCR or parsing noise | Garbled text where the deciding fact should be | v2: parser |

### I — Information not available (no model could have known from the facts)

| Code | Name | Evidence test | Goes to |
|---|---|---|---|
| I1 | Decided on records not in facts | Findings turn on a discharge summary, test report or proposal form that the complaint does not describe | Limitations: "outcome depends on documents" |
| I2 | Discretion or ex-gratia | Ombudsman awards a goodwill or ex-gratia payment despite agreeing with the insurer | Limitations; possible label-policy note |
| I3 | Procedural outcome | Time-barred, outside jurisdiction, withdrawn, settled before hearing | Should be out of scope; dataset filter in v2 |
| I4 | New evidence at hearing | Findings rely on facts first raised at the hearing | Limitations |

### M — Model (the information was there and the model misused it)

| Code | Name | Evidence test | Goes to |
|---|---|---|---|
| M1 | Reason shortcut | Prediction matches the majority label for this `rejection_reason` while the facts point the other way (e.g. non-disclosure of an **unrelated** condition) | Limitations; v2 contrast examples |
| M2 | Partial boundary | Right on "any payment" but wrong on full vs part payment (deductions, sub-limits, room-rent) | v2: amount features |
| M3 | Jurisdiction confusion | The case turns on a rule specific to one country and the model followed another country's pattern | Fairness plan (country slice) |
| M4 | Rare pattern | Train cell `(rejection_reason, country)` has < 20 records, or the condition family is rare | v2: more data |
| M5 | Temporal drift | The outcome depends on a rule that changed after the training window (e.g. Indian health-insurance regulations revised in 2024 on moratorium and waiting periods — confirm the exact changes before citing) | Limitations; retraining cadence |
| M6 | Language misread | Negation, hedging or a quoted insurer argument read as the complainant's position | v2 |

### C — Confidence and abstention (the error should not have reached the user)

| Code | Name | Evidence test | Goes to |
|---|---|---|---|
| C1 | Should have abstained | Wrong with P ≥ 0.80, or off-topic input that passed the topic check | `abstention-policy.md` v2 review |
| C2 | Near the boundary | Top two class probabilities within 0.05 | Reported only (expected noise) |

C codes are **secondary only** unless nothing else applies, because they describe where the error escaped, not why it happened.

### X — Unclear

| Code | Name | Use |
|---|---|---|
| X1 | Cannot tell | Reading both texts, the reviewer cannot say why the model erred. Keep this honest; a large X1 share is itself a finding |

---

## 5. Assignment order

To keep coding consistent, try the codes in this order and stop at the first that fits as **primary**:

```text
1. D1  Is the gold label wrong?                       → D1 (and stop: not a model error)
2. D2  Did the input break the leakage contract
       or lose the insurer's position?                → D2
3. I3  Was it a procedural outcome?                   → I3
4. I1/I2/I4  Did the decision rest on information
       a user could not have given?                   → I1 / I2 / I4
5. D3/D4/D5  Was the deciding fact lost in processing? → D3 / D4 / D5
6. M5  Did a rule change after 2023 decide it?         → M5
7. M3  Does a country-specific rule decide it?         → M3
8. M2  Right on any-payment, wrong on amount?          → M2
9. M1/M4/M6  Shortcut, rare, or misread?               → M1 / M4 / M6
10. Otherwise                                          → X1
Then add C1/C2 as secondary if they apply.
```

Cases coded D1 are removed from "model errors" in the summary and reported as an estimated **label-noise rate** on misclassified test cases (with the caveat that the denominator is errors, not all records).

---

## 6. Explanation failures (separate tally)

Not part of the 50-case primary coding, because explanations do not affect the label. PR 15 reads `reports/explanations/dropped.jsonl` and `reports/audits/A6-disagreements.csv` and tallies:

| Code | Name |
|---|---|
| E1 | Invented detail (A6 `partially`) |
| E2 | Unsupported claim (A6 `unsupported`) |
| E3 | Misattribution (A6 F2) |
| E4 | Overgeneralisation (A6 F4) |
| E5 | Contradicts predicted label (A6 X1 = `opposite`) |
| E6 | Checker false drop (A6 dropped but supported) |
| E7 | Checker false keep (A6 kept but not supported) |

---

## 7. Reviewer consistency

After a gap of at least 7 days, re-code 10 of the 50 cases blind. Report agreement on the primary **letter** (D/I/M/C/X) and on the full code, with Cohen's κ for the letter. Where the two codings disagree, the later one is not automatically right; note both and keep the first in the tallies.

---

## 8. Coding sheet and outputs

`reports/audits/ERR-<date>.csv`:

```text
doc_id, country, true_label, pred_label, p_pred, stratum, primary_code,
secondary_codes, deciding_fact (one line, anonymised), in_facts (y/n),
truncated (y/n), train_cell_n, note
```

`reports/error-analysis.md` (written in PR 15) contains:

1. Sample counts per stratum vs targets
2. Tally by letter and by code, overall and for India
3. Cross-tab: primary code × stratum (false discouragement, false hope, partial, high-confidence)
4. Three to five short anonymised case vignettes, one per major code, written in your own words
5. Explanation-failure tally (§6)
6. Estimated label-noise rate (D1)
7. Actions: each code with ≥ 3 cases mapped to a limitations line or a `backlog-v2.md` item

### Reading the result

| Pattern | What it suggests |
|---|---|
| I-codes dominate | The ceiling is the information users can give; better models will not help much. Strong limitations statement |
| M1 dominates | The model leans on the rejection reason; the B2 baseline gap is smaller than it looks |
| M5 concentrated in recent quarters | Retraining cadence matters; ties to the drift check in `evaluation-protocol.md` §7 |
| C1 large | Abstention threshold too permissive for high-confidence errors; v2 review |
