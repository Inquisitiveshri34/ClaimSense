# ClaimSense — Limitations

> What ClaimSense cannot do and where its numbers should not be trusted. Each limitation says where it comes from, how it bends the results, how it is measured, and what users are told. Numbers marked ⟨PR 14⟩ or ⟨PR 15⟩ are filled from the evaluation report and error analysis before the v1.0 tag. A limitation that is measured and stated is part of the result; one that is hidden is a defect.

**Author:** Diya Shrivastava · **Owning PR:** 18 (findings from PR 14, PR 15 and PR 16) · **Status:** Planned; numbers pending

**Related:** `../04-data-sources.md` §8, `../evaluation/evaluation-protocol.md` §7–§8, `../evaluation/fairness-analysis-plan.md` §7, `../evaluation/error-taxonomy.md`, `../modelling/calibration.md`, `../modelling/abstention-policy.md`, `../data/labelling-guide.md`, `../data/anonymisation-spec.md`, `responsible-use.md`, `privacy-impact-assessment.md`, `MODEL_CARD.md`, risks R1, R3, R6, R7, R10, R12, R13.

---

## 1. Summary

| ID | Limitation | Direction of effect | Severity | Measured in |
|---|---|---|---|---|
| **L1** | **Selection bias**: only disputes that reached an ombudsman and ended in a published decision | Estimates describe escalated cases, not all rejected claims | High | Not measurable from the data; stated |
| **L2** | **Jurisdiction shift**: UK and Irish law, policies and procedure differ from India's | Lower or unstable accuracy for Indian users | High | India-only tables; cross-country transfer (PR 14) |
| **L3** | **Label noise**: Indian outcomes mapped from free-text awards by rules | Caps achievable accuracy; blurs `partially_upheld` | Medium | 100-document label audit; D1 code in error analysis |
| **L4** | **Drift**: rules, policy wording and ombudsman practice change over time | Accuracy falls on newer disputes | Medium | Temporal split; E1 by quarter (PR 14) |
| **L5** | **Input shift**: trained on facts written by the ombudsman, used on accounts written by users | Real-use accuracy likely below test accuracy | High | Not measured in v1; stated |
| **L6** | **Information ceiling**: the model sees a short description, not the evidence | Many outcomes cannot be predicted from facts alone | High | Facts-vs-findings gap; I-codes in error analysis |
| L7 | Parsing and segmentation errors | Wrong text in input or explanation | Low | Segmenter ≥ 95% on 50 hand-checked documents |
| L8 | Anonymisation side effects | Lost detail that decided some cases | Medium | Over-removal rate (PR 6); error analysis |
| L9 | Small data and uncertainty | Wide confidence intervals; weak minority class | Medium | Bootstrap CIs; per-class F1 |
| L10 | Calibration holds only in distribution | "70%" can be wrong for unusual inputs | Medium | ECE per slice |
| L11 | Explanations describe precedents, not the model | Explanation can disagree with the estimate | Medium | E5 tally; faithfulness audit |
| L12 | Similar text is not legal relevance | A close precedent may turn on a different point | Medium | Reason match@5; retrieval rubric |
| L13 | Abstention leaves gaps | Some users get no estimate | Low | Coverage and abstain rate per slice |
| L14 | Data mix depends on permissions | Source balance may differ from the plan | Medium | Data card |
| L15 | Narrow scope | English, health insurance, rejected claims only | Low | Abstention codes |

---

## 2. The four core limitations

### L1 · Selection bias

**Where it comes from.** Most rejected claims never reach an ombudsman. A dispute enters the dataset only if the person complained to the insurer, was still unhappy, filed with the ombudsman within the time limits, the complaint was accepted, it was not withdrawn or settled first, and it ended in a published decision. Each step filters cases, and not at random: people with stronger cases, more money at stake, or more time and confidence are more likely to get through. Non-entertainable, withdrawn and settled cases are excluded on purpose (`labelling-guide.md`).

**How it bends the results.**

- Outcome rates in the data are **not** the chance that a rejected claim is overturned in general. They are rates among escalated, decided cases.
- Weak complaints that people abandoned early are missing, so the model may be **more optimistic** than reality for the typical rejected claim.
- Some disputes, such as clear-cut repudiations insurers usually reverse once challenged, may be under-represented because they settle before a decision.

**How it is measured.** It cannot be measured from this data; there is no record of the claims that were never escalated. The base-rate table (`fairness-analysis-plan.md` §5) shows the label distribution that is learned.

**What users are told.** "ClaimSense learned only from disputes that reached an ombudsman and were decided. It knows nothing about claims that were settled, withdrawn or never escalated."

### L2 · Jurisdiction shift

**Where it comes from.** India is the primary user base, but training uses UK and Irish decisions too, because Indian volume alone may be too small (D11, R1). The three systems differ in:

| Area | Examples of difference |
|---|---|
| Regulation | IRDAI standard exclusions and waiting periods vs UK and Irish rules |
| Policy products | Mediclaim, family floater and group policies vs UK private medical insurance |
| Ombudsman procedure | Award vs final decision; different powers, limits and writing styles |
| Base rates | Uphold rates differ by ombudsman |
| Currency and amounts | INR vs GBP/EUR; amount bands converted at a fixed rate |

**How it bends the results.** A pattern that predicts outcomes in the UK may not hold in India. Pooled metrics can look good while Indian performance is poor. If PR 3's checkpoint triggered (< ~800 usable Indian awards), India is test-only and every Indian prediction is out of distribution.

**How it is measured (PR 14).**

| Measure | Value |
|---|---|
| Macro-F1, all test [95% CI] | ⟨PR 14⟩ |
| Macro-F1, India only [95% CI] | ⟨PR 14⟩ |
| Macro-F1 on India, trained **without** India | ⟨PR 14⟩ |
| ECE, India only | ⟨PR 14⟩ |
| Coverage at chosen τ, India vs all | ⟨PR 16⟩ |
| India in training data? | ⟨yes / no: R1 contingency applied⟩ |

**What users are told.** Every precedent shows its country and ombudsman; the jurisdiction note appears when most precedents are foreign (`responsible-use.md` §2.6); the Model Card leads with India-only results.

### L3 · Label noise

**Where it comes from.**

- CIOINS awards state outcomes in free text ("directed to pay", "repudiation sustained", "settle as per terms"). Rules map them to three classes, and some wording is ambiguous.
- `partially_upheld` is a wide class: a small top-up, a direction to reconsider, and most of the claim paid all land in it.
- FOS has no partial class in its listing metadata, so FOS partial outcomes are folded into `upheld` or found only by hand.
- FSPO's "substantially upheld" is mapped to `upheld`.

**How it bends the results.** Noise sets a ceiling on accuracy and makes the boundary between `upheld` and `partially_upheld` blurry. Errors between those two classes partly reflect labels, not the model.

**How it is measured.**

| Measure | Value |
|---|---|
| Label accuracy on the 100-document hand-checked sample | ⟨PR 6⟩ (assumption: ≥ 95%) |
| Accuracy by source (CIOINS / FOS / FSPO) | ⟨PR 6⟩ |
| Misclassified test cases coded D1 (label error) in error analysis | ⟨PR 15⟩ of 50 |
| Macro-F1 on the binary "any payment" view | ⟨PR 14⟩ (less affected by the partial boundary) |

**What users are told.** "Upheld" and "partly upheld" are shown with all three probabilities so a close call is visible; the Model Card states the label accuracy.

### L4 · Drift

**Where it comes from.** Health-insurance rules and practice change: regulators revise standard exclusions and waiting periods, insurers rewrite policy wording, and ombudsman practice shifts. The model learns from decisions up to 2023 and is validated on 2024.

**How it bends the results.** Patterns that were true before a rule change can be wrong after it. Precedents from before the change can mislead. Calibration fitted on 2024 can drift by 2026.

**How it is measured (PR 14).**

| Measure | Value |
|---|---|
| Test period | 2025 onward |
| Macro-F1 by decision quarter | ⟨PR 14⟩ (trend noted) |
| Errors coded M5 (rule or practice change) and their quarters | ⟨PR 15⟩ |

**What users are told.** Each precedent shows its decision year. The Model Card states the training window and that the dataset is frozen per version (no live updates in v1).

---

## 3. Further limitations

### L5 · Input shift: ombudsman-written facts vs user-written accounts

The model is trained on the **complaint and insurer-position sections written by the ombudsman's office**: a neutral summary, prepared after reading both sides' documents, in a consistent style. In the app the input is the **user's own account**: shorter, one-sided, often missing the insurer's exact reason or the policy clause, and written under stress.

This is a train/serve mismatch the temporal test set does not capture, because test inputs are also ombudsman-written. Real-use accuracy is therefore **likely lower than the reported test accuracy**, by an amount v1 does not measure. The topic check and `NO_PRECEDENTS` floor catch some very different inputs, not all.

*v2:* collect a small set of user-style rewrites of test cases and measure the gap (candidate backlog item).

### L6 · Information ceiling

Outcomes often turn on evidence the model never sees: discharge summaries, the date of first diagnosis in medical records, the exact clause wording, what was disclosed on the proposal form. ClaimSense predicts from a description of these, not from the documents.

| Measure | Value |
|---|---|
| Facts-only macro-F1 vs findings-included ceiling (B3) | ⟨PR 14⟩ |
| Misclassified cases coded I (deciding fact absent from facts) | ⟨PR 15⟩ of 50 |

If I-codes dominate the error analysis, better models will not fix this; the limit is the information available.

### L7 · Parsing and segmentation errors

OCR on scanned awards produces misread words and numbers; segmentation can put a sentence of findings into facts (a leakage risk, guarded by leak probes, NFR-01) or drop part of the facts. Documents that cannot be segmented are excluded with a logged count, which removes the messiest layouts, often from particular offices.

| Measure | Value |
|---|---|
| Segmenter accuracy on 50 hand-checked documents | ⟨PR 5⟩ (gate ≥ 95%) |
| Documents dropped as unsegmentable, by source and office | ⟨PR 5⟩ |
| Share of CIOINS documents needing OCR | ⟨PR 5⟩ |

### L8 · Anonymisation side effects

Privacy controls remove detail that sometimes decided a case:

| Removed or generalised | Cases affected |
|---|---|
| Exact dates → month/year | Waiting-period disputes decided by days (for example, an admission a few days before or after an initial waiting period ends) |
| Hospital names → `[PROVIDER]` | Network/non-network hospital disputes; disputes about a specific provider's billing |
| Exact ages → ten-year bands | Age-limit clauses and age-linked co-payments |
| Employer → `[EMPLOYER]` | Group-policy disputes tied to employer terms |

Over-removal rate (tokens wrongly replaced) ⟨PR 6⟩.

### L9 · Small data and uncertainty

The dataset is modest after filtering to health, and the test split covers about one year. Confidence intervals are wide; `partially_upheld` is the smallest class (R7); slices below n = 30 report counts only. Two models whose intervals overlap should not be called different.

| Measure | Value |
|---|---|
| Records per split and class | ⟨PR 7⟩ |
| Per-class F1 [95% CI] | ⟨PR 14⟩ |

### L10 · Calibration holds only in distribution

Calibration is fitted on 2024 validation data (`calibration.md`). It is reliable for inputs like that data, not for unusual cases, foreign-jurisdiction cases or user-written text (L5). A slice can be well calibrated overall but systematically too low on "any payment" for one group (`fairness-analysis-plan.md` §5).

| Measure | Value |
|---|---|
| Test ECE, all [CI] | ⟨PR 12/14⟩ (target ≤ 0.05) |
| Test ECE, India | ⟨PR 14⟩ |
| Predicted vs observed P(any payment), per slice | ⟨PR 15⟩ |

### L11 · Explanations describe precedents, not the model

The classifier and the explanation are **separate steps**. The explanation is written by an LLM from the retrieved precedents' findings; it is not an account of why the classifier chose its label. It can therefore summarise precedents that went the other way. The citation checker confirms that each sentence is supported by a cited precedent, not that the sentence is the most relevant point, and the NLI checker itself makes mistakes.

| Measure | Value |
|---|---|
| Explanation sentences with a valid citation (after filter) | 100% by construction |
| Manual faithfulness agreement (40-case audit) | ⟨PR 15⟩ (target ≥ 90%) |
| Explanations contradicting the predicted label (E5) | ⟨PR 15⟩ |
| Checker false keeps / false drops (E7 / E6) | ⟨PR 15⟩ |
| Empty-explanation rate | ⟨PR 16⟩ |

### L12 · Similar text is not legal relevance

Retrieval uses embedding similarity. Two cases can read alike yet turn on different points (pre-existing disease vs the waiting-period clause), and a decisive precedent may use different words. Precedents come only from earlier decisions, so the newest relevant rulings are always missing for a case at the edge of the data.

| Measure | Value |
|---|---|
| Rejection-reason match@5 | ⟨PR 14⟩ |
| Hand-rated relevance (retrieval rubric) | ⟨PR 15⟩ |

### L13 · Abstention leaves gaps

By design, ClaimSense refuses some inputs. Coverage is targeted at ≥ 0.50 on validation; coverage may be lower for India, rare conditions and unusual disputes, which are often the users who most need help.

| Measure | Value |
|---|---|
| Coverage at chosen τ: all / India / UK / Ireland | ⟨PR 16⟩ |
| Abstain rate by code | ⟨PR 16⟩ |

### L14 · Data mix depends on permissions

FOS and CIOINS collection waits for permission (`terms-of-use-audit.md` §1). If either is refused, the dataset differs from the plan and L2 changes with it. The v1.0 data card states which sources were used and under what terms.

| Source | Used in v1.0? | Terms |
|---|---|---|
| CIOINS | ⟨PR 7⟩ | ⟨permission status⟩ |
| FOS | ⟨PR 7⟩ | ⟨permission status⟩ |
| FSPO | ⟨PR 7⟩ | PSI re-use, attribution |

### L15 · Narrow scope

English only; health insurance only; disputes about a rejected or partly paid claim. Not covered: other insurance lines, delay-only or interest-only complaints, critical-illness and disability lump sums, non-English input, policy or letter uploads (`scope.md` §3, `abstention-policy.md` §5).

---

## 4. Findings from evaluation

Filled in PR 18 from `reports/fairness/differences.csv` and `reports/error-analysis.md`. Every slice that meets a flag rule (`fairness-analysis-plan.md` §6) and every error code with ≥ 3 cases gets one row.

| Finding | Evidence | Likely cause (`fairness-analysis-plan.md` §5) | What users are told |
|---|---|---|---|
| ⟨e.g. higher false-discouragement rate for claims under ₹50k⟩ | ⟨FD rate [CI] vs best slice⟩ | ⟨world differs / model / cannot tell⟩ | ⟨flagged-slice note text⟩ |
| | | | |

If no flag fires, write: "No slice met a flag rule at the test-set sizes available; small slices were not tested and may still differ."

---

## 5. Not limitations of the model, but worth stating

- **It cannot predict amounts.** The label says whether money was ordered, not how much.
- **It cannot predict time.** Nothing in the data says how long an ombudsman complaint takes.
- **It says nothing about any insurer's overall behaviour.** Escalated complaints are a skewed sample (`responsible-use.md` §4).
- **Results are for one model run on one frozen dataset version.** Any rebuild needs a new evaluation report.

---

## 6. Short version (for the Model Card page and README)

> ClaimSense learned from health-insurance disputes that reached ombudsmen in India, the UK and Ireland and ended in a published decision; it knows nothing about claims that were settled or never escalated. UK and Irish rules differ from India's, and results for Indian cases are reported separately: ⟨India macro-F1⟩ vs ⟨overall macro-F1⟩. Outcomes in Indian awards were labelled by rules and are about ⟨label accuracy⟩ correct. The model was trained on decisions up to 2023 and tested on 2025 onward; rules may have changed since. It was trained on case summaries written by the ombudsman, not by users, so real-world accuracy is likely lower than reported. It cannot see your documents, and it declines to answer about ⟨100 − coverage⟩% of the time.

---

## 7. Maintenance

| Trigger | Action |
|---|---|
| New dataset version | Re-run PR 14–16 evaluation; refill every ⟨⟩ value; re-check L1 wording against new exclusions |
| New source added | Update L2 and L14; re-run cross-country transfer |
| Regulator changes standard exclusions or waiting periods | Add a dated line under L4; consider a new dataset version |
| LLM provider or model change | Re-run the faithfulness audit; update L11 |
| User-style evaluation set built (v2) | Replace the "not measured" text in L5 with numbers |

### Tests (PR 18)

| Test | Checks |
|---|---|
| `test_limitations_filled` | No ⟨⟩ placeholder remains in `limitations.md` at the v1.0 tag |
| `test_limitations_numbers_match_report` | Numbers in §2 tables equal the values in `reports/metrics.json` for the tagged run |
| `test_model_card_links_limitations` | `MODEL_CARD.md` links this file and includes the §6 short version |
| `test_flags_written_up` | Every flagged row in `differences.csv` appears in §4 |

---

*ClaimSense describes how similar past cases were decided. It is not legal advice; the ombudsman decides each case on its own facts.*
