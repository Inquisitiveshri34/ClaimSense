# ClaimSense — EDA Findings

> Written findings from the exploratory data analysis of dataset v1. Read this before PR 9: every modelling choice that follows (class weights, truncation length, which slices to watch) should trace back to a finding here.

**Author:** Diya Shrivastava · **Owning PR:** 8 (`analysis/eda`) · **Status:** Draft / Final
**Notebook:** `notebooks/08-eda.ipynb` · **Figures:** `reports/figures/eda/`
**Related:** `data/dataset-versioning.md`, `data-schema.md` §4, `evaluation-protocol.md` §3, §8, `modelling/baselines.md`, `planning/risk-register.md` (R7, R13)

---

## 0. Run details

| Item | Value |
|---|---|
| Dataset version | `v________` (from `data/processed/LATEST`) |
| Evaluation protocol | Tagged `eval-protocol-v1` on ____ (must be **before** this PR) |
| Git SHA of notebook run | `________` |
| Run date | ____-__-__ |
| Splits analysed | `train` + `val` only |
| Test split | **Counts only** (n per source, copied from `DATA_CARD.md`); no label, text or slice analysis (L3) |

> **Rule:** this EDA does not open `test.parquet`. Looking at test label balance or text before the report would weaken the pre-registration in `evaluation-protocol.md`.

---

## 1. Summary (fill last)

Five to seven one-line findings, most important first. Each one names its section and what it changes.

| # | Finding | Section | What it changes |
|---|---|---|---|
| F1 | | | |
| F2 | | | |
| F3 | | | |
| F4 | | | |
| F5 | | | |

---

## 2. Dataset snapshot

### 2.1 Size per split and source

| Source | Country | Train (≤ 2023) | Val (2024) | Test (2025+, count only) | Total |
|---|---|---|---|---|---|
| `cioins` | IN | | | | |
| `fos` | GB | | | | |
| `fspo` | IE | | | | |
| **Total** | | | | | |

- Test size ≥ 150? ☐ yes ☐ no → if no, note it here; `evaluation-protocol.md` §3 requires the report to say so first.
- Risk R1 checkpoint (≥ ~800 usable Indian awards): ☐ met ☐ not met → training plan used: ____________

### 2.2 Funnel (from `funnel.csv`)

| Stage | cioins | fos | fspo | Note |
|---|---|---|---|---|
| Listed | | | | |
| Downloaded | | | | |
| Parsed | | | | |
| Segmented | | | | |
| Labelled | | | | |
| After dedup | | | | |
| **Usable** | | | | |

Largest drop-off and its cause: ______________________

---

## 3. Outcome balance

### 3.1 Overall and by source (train + val)

| Source | n | `upheld` | `partially_upheld` | `rejected` | Any payment (`label_binary`) |
|---|---|---|---|---|---|
| cioins | | __ (__%) | __ (__%) | __ (__%) | __% |
| fos | | | | | |
| fspo | | | | | |
| **All** | | | | | |

Figure: `figures/eda/label_by_source.png`

**Finding:** ______________________
**Implication for R7 (imbalance):** `partially_upheld` share is __%. ☐ `class_weight="balanced"` is enough ☐ needs a note in `finetuning-spec.md` (weighted loss / sampling)

### 3.2 By decision year

| Year | n | upheld % | partial % | rejected % | Split |
|---|---|---|---|---|---|
| 20__ | | | | | train |
| … | | | | | |
| 2024 | | | | | val |

Figure: `figures/eda/label_by_year.png`

**Finding (train → val shift):** ______________________
**Implication:** a change between train and val label mix is a preview of drift that the PR 14 quarterly check (`evaluation-protocol.md` §7) will test properly.

### 3.3 By insurer type (India only)

| Insurer type | n | upheld % | partial % | rejected % |
|---|---|---|---|---|
| public | | | | |
| private | | | | |
| standalone_health | | | | |

> Pooled across countries this slice mostly measures country (UK/IE are almost all `private`), so it is shown for India only (`fairness-analysis-plan.md` §4.2). No named-insurer breakdown.

**Finding:** ______________________

### 3.4 By rejection reason

| Rejection reason | n | Share of data | upheld % | partial % | rejected % | Smallest (reason, source) cell n |
|---|---|---|---|---|---|---|
| non_disclosure | | | | | | |
| waiting_period | | | | | | |
| exclusion | | | | | | |
| not_medically_necessary | | | | | | |
| documentation | | | | | | |
| other | | | | | | |

**Finding:** ______________________
**Implication for B2 (rules baseline):** cells with n < 20 fall back (`min_cell_n`). Count of such cells: __. If one reason predicts the outcome very strongly, expect B2 to be a hard baseline and watch for the M1 "reason shortcut" in PR 15.

### 3.5 By claim amount band

| Band | n | upheld % | partial % | rejected % |
|---|---|---|---|---|
| lt_50k | | | | |
| 50k_2l | | | | |
| 2l_5l | | | | |
| gt_5l | | | | |
| unknown | | | | |

Within-country tercile cut points (from **train** amounts):

| Country | Small ≤ | Medium ≤ | Large > |
|---|---|---|---|
| IN | | | |
| GB | | | |
| IE | | | |

**Finding:** ______________________ (`unknown` share = __%; if high, flag for the fairness plan)

### 3.6 By product

| Product | n | upheld % | partial % | rejected % |
|---|---|---|---|---|
| individual_mediclaim | | | | |
| group_mediclaim | | | | |
| overseas_mediclaim | | | | |
| private_health | | | | |

**Finding:** ______________________

---

## 4. Text

### 4.1 Length of `facts_text`

| Source | Median chars | p90 chars | Median tokens* | p90 tokens* | % over model context (____ tokens) |
|---|---|---|---|---|---|
| cioins | | | | | |
| fos | | | | | |
| fspo | | | | | |

\* Tokenizer: `________` (the PR 11 base model's).

Figures: `figures/eda/facts_length_by_source.png`, `figures/eda/facts_length_by_label.png`

**Finding:** ______________________
**Implication for PR 11:** ☐ head-tail truncation at ____ tokens keeps most records whole ☐ more than __% truncated → note risk of D3 (truncation loss) errors

### 4.2 Length vs outcome

Does length alone predict the label? Median `facts_chars` by label: upheld ____ · partial ____ · rejected ____

**Finding:** ______________________ (if strong, length is a shortcut feature; mention in PR 9)

### 4.3 Outcome-word leakage (L2)

| Source | Mean `lexicon_hits` | % records with ≥ 1 hit | Top 5 lexicon words found |
|---|---|---|---|
| cioins | | | |
| fos | | | |
| fspo | | | |

Hits by label: upheld ____ · partial ____ · rejected ____

**Finding:** ______________________
**Implication:** if hits differ strongly by label, the facts text still carries outcome signal → re-check the segmenter (PR 5) before trusting baseline numbers.

### 4.4 Anonymisation tokens

| Token | Mean count per record | % records containing |
|---|---|---|
| `[PERSON]` | | |
| `[DATE]` | | |
| `[AMOUNT]` | | |
| other: ____ | | |

**Finding:** ______________________ (heavy masking of dates or amounts → watch for D4 errors in PR 15)

### 4.5 Vocabulary by source (optional)

Top distinctive terms per source (TF-IDF on train): see `figures/eda/top_terms_by_source.png`.

**Finding:** ______________________ (very source-specific vocabulary predicts weaker cross-country transfer)

---

## 5. Data quality checks

| Check | Result | Action |
|---|---|---|
| Near-duplicates removed by MinHash | __ records (__%) | |
| Same case in two splits | 0 expected | |
| `label_binary == (label != "rejected")` | ☐ holds | |
| Empty or very short `facts_text` (< ___ chars) | __ records | |
| OCR-fallback documents (Tesseract) | __% | |
| Records with `rejection_reason = other` | __% | if > 20%, the enum may be too coarse → backlog-v2 |

---

## 6. Decisions and hand-offs

| To | Decision or note |
|---|---|
| PR 9 baselines | |
| PR 11 fine-tune (truncation, class weights) | |
| PR 12 calibration (val size per class) | |
| PR 14 slices to watch | |
| `planning/risk-register.md` | Risks updated: |
| `planning/backlog-v2.md` | Ideas parked: |

---

## 7. Open questions

- [ ] ______________________
- [ ] ______________________

---

## Done-when check (PR 8)

- [ ] Notebook renders end to end from a clean kernel (`jupyter nbconvert --execute`)
- [ ] Every section above has a written finding, not only a chart
- [ ] Test split not opened (only counts from `DATA_CARD.md`)
- [ ] Figures saved under `reports/figures/eda/`
