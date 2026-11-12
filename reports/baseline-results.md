# ClaimSense — Baseline Results

> Validation-split results for the five baselines B1–B5. The best of these sets the bar the fine-tuned model must clear in PR 11. Configurations are fixed in `modelling/baselines.md`; this file records what they scored and what that means.

**Author:** Diya Shrivastava · **Owning PR:** 9 (B1–B3) · 10 (B4, B5) · **Status:** Draft / Final
**Related:** `modelling/baselines.md`, `modelling/experiment-log.md`, `modelling/prompt-spec.md` (P-ZS-v1), `leakage-contract.md` (L1–L3), `reports/eda-findings.md`

---

## 0. Run details

| Item | Value |
|---|---|
| Dataset version | `v________` |
| Split scored | **`val` (2024) only** — test is never read in PR 9/10 (L3) |
| Val size | n = ____ (upheld ____ · partial ____ · rejected ____) |
| Val any-payment base rate | ____ |
| Input field | `facts_text` only (L1) |
| Metric code | `claimsense.eval.metrics.score()` @ git SHA `________` |
| CI method | Bootstrap, 1,000 resamples of val records, seed 13 |
| Tracker | MLflow / W&B project `________` |

---

## 1. Headline table

| ID | Baseline | PR | Macro-F1 [95% CI] | F1 upheld / partial / rejected | PR-AUC any payment (base rate) | Accuracy | ECE / Brier | Run ID |
|---|---|---|---|---|---|---|---|---|
| B1 | Majority class | 9 | 0.___ [0.__, 0.__] | 0.___ / 0.___ / 0.___ | 0.___ (0.___) | 0.___ | 0.___ / 0.___ | |
| B2 | Rejection-reason rules | 9 | | | | | | |
| B3 | TF-IDF + LR | 9 | | | | | | |
| B4 | Embeddings + LR | 10 | | | | | | |
| B5 | Zero-shot LLM | 10 | | | | | | |

**Best baseline on val macro-F1:** B__ at 0.___ [0.__, 0.__] → **this is the bar for PR 11.**
**Headline comparison for PR 14:** B3 (fixed in advance, whatever the val ranking).

Figure: `reports/figures/baselines/macro_f1_ci.png` (point + CI per baseline)

---

## 2. Per-baseline detail

### B1 — Majority class

| Item | Value |
|---|---|
| Predicted class | `________` (train share ____) |
| PR-AUC = base rate? | ☐ yes (expected; constant score) |

**Reading:** This is the "knowing nothing" floor. Any model below it on macro-F1 is broken.

### B2 — Rejection-reason rules

| Item | Value |
|---|---|
| Cells used at `(reason, source)` level | __ of __ |
| Backed off to reason only | __ |
| Backed off to global prior | __ |

Learned lookup (most frequent label per cell):

| Rejection reason | cioins | fos | fspo |
|---|---|---|---|
| non_disclosure | | | |
| waiting_period | | | |
| exclusion | | | |
| not_medically_necessary | | | |
| documentation | | | |
| other | | | |

> **Caveat (must stay in the report):** B2 reads the dataset's `rejection_reason` column, which a live user does not supply. It is therefore slightly optimistic, which makes it a stronger baseline.

**Reading:** ______________________

### B3 — TF-IDF + logistic regression

| Item | Value |
|---|---|
| Chosen `C` | ____ (grid 0.1 / 0.3 / 1 / 3 / 10; ties → smaller) |
| Vocabulary size | ____ |
| Val macro-F1 per `C` | 0.1: ____ · 0.3: ____ · 1: ____ · 3: ____ · 10: ____ |

Top terms (full list: `reports/baselines/b3_top_terms.csv`):

| Class | Top 10 positive terms |
|---|---|
| upheld | |
| partially_upheld | |
| rejected | |

**L2 leakage check:** outcome words (*wrongly*, *unfair*, *allowed*, *dismissed*, …) in the top 30? ☐ none ☐ found: ____________ → noted in PR description and checked against `tests/leak/`.

**Reading:** ______________________

### B4 — Sentence embeddings + logistic regression

| Item | Value |
|---|---|
| Encoder | `BAAI/bge-small-en-v1.5` (same as retrieval) |
| Pooling | chunk-mean, 400-token windows, 50 overlap |
| Chosen `C` | ____ |
| Embedding cache | `data/cache/emb/<encoder>/<dataset_version>.npy` |

**PR 10 done-when:** B4 beats B3 on val macro-F1? ☐ yes (Δ = +0.___) ☐ no → explanation:

> ______________________ (embeddings often lose to TF-IDF on long, domain-specific text; that is a valid result)

### B5 — Zero-shot LLM

| Item | Value |
|---|---|
| Prompt ID | `P-ZS-v1` |
| Provider / model | ____ / `________` (pinned) |
| Temperature | 0 |
| Records sent | ____ (val only) |
| Parse failures after 1 retry | __ (__%) → assigned train majority class |
| Parse-failure rate > 2%? | ☐ no ☐ yes → new prompt version needed |
| Cache hit rate on re-run | ____% |
| Provider data-retention terms checked | ☐ yes, noted in `prompt-spec.md` §3 |
| Only anonymised `facts_text` sent | ☐ confirmed |

Verbalised probabilities: ECE ____ (expected to be poor; that is part of what B5 shows).

**Reading:** ______________________

---

## 3. Confusion matrices (val)

Rows = true, columns = predicted. Files: `reports/baselines/<id>_confusion.csv`.

**B3**

| true \ pred | upheld | partial | rejected |
|---|---|---|---|
| upheld | | | |
| partially_upheld | | | |
| rejected | | | |

**B5**

| true \ pred | upheld | partial | rejected |
|---|---|---|---|
| upheld | | | |
| partially_upheld | | | |
| rejected | | | |

(Add B2 / B4 if they tell a different story.)

**Reading:** Is `partially_upheld` ever predicted correctly? ______________________

---

## 4. By source (val, exploratory)

Metrics only where n ≥ 30; otherwise counts.

| Baseline | cioins macro-F1 | fos macro-F1 | fspo macro-F1 |
|---|---|---|---|
| B2 | | | |
| B3 | | | |
| B4 | | | |
| B5 | | | |

**Reading:** ______________________

---

## 5. What these numbers mean

1. **How much does text add over the rejection reason?** B3 − B2 = ____ macro-F1. ______________________
2. **Do semantic features help?** B4 − B3 = ____. ______________________
3. **Is fine-tuning worth trying?** B5 vs B3 = ____. If prompting a large model already beats every classic baseline, the PR 11 claim has to be "fine-tuning beats prompting", not just "beats TF-IDF".
4. **Weakest class:** `________`, best F1 among baselines = ____.

---

## 6. The bar for PR 11

| Check | Value |
|---|---|
| Val macro-F1 the fine-tuned model must exceed (each of B1–B5) | **0.___** (B__) |
| `partially_upheld` F1 to beat (from B3) | 0.___ |
| PR-AUC to beat (from B3) | 0.___ |
| If not met | Report honestly; ship the strongest model (risk R8) |

---

## Done-when checks

- [ ] PR 9: macro-F1 and PR-AUC logged for B1, B2, B3 with run IDs
- [ ] PR 10: B4 and B5 logged; B4/B5 beat B3 or the gap is explained above
- [ ] `tests/test_baselines.py` green (`no_test_split`, `deterministic`, `b2_backoff`, `b5_parser`)
- [ ] Results copied into `modelling/baselines.md` §4
