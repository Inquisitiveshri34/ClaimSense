# ClaimSense — Fairness Analysis Plan

> How ClaimSense checks whether its errors fall unevenly on different kinds of claims and claimants: the slices (insurer type, claim size, country), the harm-weighted metrics for each, how model gaps are separated from genuine differences in ombudsman outcomes, the flag rules fixed in the evaluation protocol, and what a flagged finding changes in v1.

**Author:** Diya Shrivastava · **Owning PR:** 15 (slices and flag rules fixed in PR 7) · **Status:** Planned

**Related:** `evaluation-protocol.md` §4 (E9), §5, §8, `error-taxonomy.md`, `../architecture/data-schema.md` §1 (`InsurerType`, `ClaimAmountBand`, `Country`), `../modelling/calibration.md`, `../modelling/abstention-policy.md`, `../responsible-ai/privacy-impact-assessment.md`, `../responsible-ai/limitations.md`, `../responsible-ai/responsible-use.md`, `MODEL_CARD.md`.

---

## 1. What "fair" means for ClaimSense

ClaimSense collects **no** personal attributes of claimants: no gender, age, religion, caste or income. Names and identifiers are removed before any processed write (`privacy-impact-assessment.md`). So this is **not** a protected-attribute audit, and it cannot be one.

What it can check is whether the tool works worse, or fails in a more harmful direction, for **kinds of claims** that map to kinds of people:

| Slice | Why it matters to people |
|---|---|
| **Claim size** | Small claims are more often from people who cannot afford a lawyer and are most likely to rely on a free tool |
| **Insurer type** | Public-sector insurers serve much of India's mass market and government-linked group policies |
| **Country** | ClaimSense is built mainly for Indian users but trained on three jurisdictions; a model that works for UK cases and not Indian ones fails its main users |

The question for each slice: **does a person in this group get a less accurate, less calibrated, or more discouraging answer than others?**

---

## 2. Harm model

Not all errors cost the same. Using the binary "any payment" view (`label_binary`):

| Error | Definition | Harm | Weight in this plan |
|---|---|---|---|
| **False discouragement (FD)** | True any-payment, predicted `rejected` | Person may abandon a claim they would have won. Money lost, no second chance once time limits pass | **Primary** |
| **False hope (FH)** | True `rejected`, predicted any-payment | Time and effort spent on a losing complaint; disappointment | Secondary |
| **Abstention burden** | `predict()` refuses | No answer; the person is no worse off than without the tool, but the tool serves them less | Reported |
| **Miscalibration** | Stated probability far from observed rate | Every decision built on the number is distorted | Reported |

FD rate = FD / (true any-payment). FH rate = FH / (true rejected). Both are conditional on the true outcome so they are comparable across slices with different base rates.

---

## 3. Metrics per slice value

Computed on **test**, model under test, by `python -m claimsense.eval slices` (called from the report command; no separate test load).

| Metric | Coverage | Minimum n |
|---|---|---|
| n, label distribution (upheld / partial / rejected) | — | always printed |
| Macro-F1 [95% CI] | full (abstention off) | 30 |
| PR-AUC any payment, with slice base rate | full | 30 |
| **FD rate**, **FH rate** [95% CI] | full | 30 true-positive / 30 true-negative records respectively |
| Mean predicted P(any payment) vs observed rate | full | 30 |
| ECE | full | 100 (else Brier) |
| Abstain rate and abstain codes | selective | 30 |
| Selective macro-F1 | selective | 30 answered |
| Automatic reason match@5 (dataset labels) | all | 30 |
| Empty-explanation rate | selective | 30 |

Below the minimum, only counts are printed (`evaluation-protocol.md` §5). Slices are never merged after seeing results.

---

## 4. Slices in detail

### 4.1 Country (primary)

Values `IN`, `GB`, `IE`. Plus, from `evaluation-protocol.md` §7: India-only full tables and the cross-country transfer run (trained without India, tested on India).

**Expected confound:** the three ombudsmen differ in procedure, in what reaches them, and in base uphold rates. A lower macro-F1 for one country can come from harder cases rather than a worse model. §5 shows how this is separated.

### 4.2 Insurer type (within India)

Values `public`, `private`, `standalone_health`.

The public/private/standalone split is an Indian market structure. In the UK and Ireland nearly all health insurers fall under `private`, so a pooled insurer-type slice would mostly measure country. **Insurer type is therefore analysed within India only.** A pooled table is printed for completeness and labelled as confounded by country.

No analysis is done by **named** insurer. The dataset holds only escalated complaints, which are a skewed sample of each insurer's claims; per-insurer error rates would invite conclusions about companies that the data cannot support.

### 4.3 Claim size

Two views, because currency conversion distorts one band scheme across countries:

| View | Bands | Use |
|---|---|---|
| **Fixed INR bands** (`ClaimAmountBand`) | `lt_50k`, `50k_2l`, `2l_5l`, `gt_5l`, `unknown` | India, and the pooled table. GBP/EUR converted at the fixed rate in `config.yaml` |
| **Within-country terciles** | small / medium / large, cut on **train** amounts per country | Cross-country comparison without conversion effects |

`unknown` is reported as its own value. If `unknown` is common, its performance matters: these are often documentation disputes, and they may be the cases where users also cannot state an amount.

### 4.4 Intersections

Printed only where both values have n ≥ 30:

- country × claim-size tercile
- India: insurer type × claim band

No further intersections. With a small test set, deeper cuts produce noise that looks like findings.

### 4.5 Secondary slices (reported, no flag rules)

`rejection_reason`, `product` (individual / group / overseas mediclaim / private health), decision quarter. These feed `error-taxonomy.md` readings and the drift check.

---

## 5. Separating model gaps from data gaps

A slice can look worse for two different reasons:

1. **The world differs.** Ombudsmen uphold small claims more often, or Irish cases are harder to predict from facts.
2. **The model treats the slice worse.** Same difficulty, worse answers.

Three checks help tell them apart:

| Check | How | Reading |
|---|---|---|
| **Base-rate table** | Label distribution per slice value (train and test) | Large base-rate differences alone explain some metric gaps; FD/FH rates are conditional on truth, so they are less affected |
| **Calibration-in-the-large** | Mean predicted P(any payment) vs observed rate, per slice | If the model predicts 40% payment where 60% occurred, it systematically discourages that slice — a model problem, regardless of base rate |
| **Baseline comparison** | Same slice metrics for B3 | If B3 shows the same gap, the slice is likely harder in the data; if only the fine-tuned model shows it, the model introduced it |

The write-up for every flagged slice states which of the three explanations the evidence supports, or that it cannot tell.

---

## 6. Flag rules (fixed in `evaluation-protocol.md` §8)

A slice result is a **finding** when, with both compared values at their minimum n:

1. Macro-F1 gap between best and worst value **> 0.10** and their 95% CIs do not overlap.
2. FD-rate ratio worst/best **> 1.5** and the bootstrap CI of the difference excludes 0.
3. ECE **> 0.10** in any value with n ≥ 100.
4. Abstain-rate ratio worst/best **> 2.0**.

Differences use the paired-index bootstrap (1,000 resamples, seed 13, stratified by source). Slice analyses are exploratory: no multiple-comparison correction is applied, and the report says so. The flags require CI evidence so a single noisy point estimate cannot trigger one.

---

## 7. What a finding changes in v1

Nothing in the v1 model, thresholds or prompts changes on the basis of test slices (`evaluation-protocol.md` §3). A finding changes what users and reviewers are told:

| Where | What is added |
|---|---|
| `limitations.md` | The finding in plain words, with numbers and the §5 explanation |
| `MODEL_CARD.md` | "Performance by group" table with every slice, flagged rows marked |
| Streamlit app | A short note on the result when the input falls in a flagged slice, e.g. "ClaimSense has seen fewer decisions like yours from Ireland; treat this estimate with extra caution." The note is triggered by metadata the user gives (country, approximate amount), never inferred about the person |
| `backlog-v2.md` | Candidate fixes, each to be chosen and tuned on **val** in v2: slice-specific abstention thresholds, reweighting or more data for the slice, a separate calibrator per country |

A flag on **FD rate** gets priority in the write-up because it is the error most likely to cost a user money.

---

## 8. Output

`reports/fairness/` (generated):

```text
slices.csv                # one row per slice value: every §3 metric with CIs
differences.csv           # pairwise differences with CIs, flag column
base_rates.csv            # label distribution per slice, train and test
figures/                  # FD/FH rates by slice, calibration-in-the-large by slice
```

Summary table in `reports/error-analysis.md` and `evaluation-report.md` §9:

| Slice | Value | n | Macro-F1 [CI] | FD rate [CI] | FH rate [CI] | Pred vs obs P(pay) | ECE / Brier | Abstain | Flag |
|---|---|---|---|---|---|---|---|---|---|
| country | IN | | | | | | | | |
| country | GB | | | | | | | | |
| country | IE | | | | | | | | |
| insurer (IN) | public | | | | | | | | |
| insurer (IN) | private | | | | | | | | |
| insurer (IN) | standalone_health | | | | | | | | |
| claim band | lt_50k | | | | | | | | |
| … | | | | | | | | | |

```text
src/claimsense/eval/slices.py     # slice_metrics(), slice_differences(), flags()
```

| Test | Checks |
|---|---|
| `test_slice_min_n` | Values below minimum n print counts only |
| `test_fd_fh_definitions` | FD/FH rates on a hand-built fixture match expected values |
| `test_insurer_type_within_india` | Insurer-type flags are computed on India records only |
| `test_terciles_from_train` | Tercile cut points come from train amounts, not test |
| `test_flag_rules` | Each of the four rules fires on a fixture built to trigger it and not on one built to pass |
| `test_no_named_insurer` | No slice key is an insurer name |
