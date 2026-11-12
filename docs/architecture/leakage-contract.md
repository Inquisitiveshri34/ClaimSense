# ClaimSense — Leakage Contract

> The rules that keep the answer out of the question. A decision document contains both the facts of a dispute and the ombudsman's verdict; if any part of the verdict reaches the model, accuracy measures reading, not prediction. This file defines the four document sections, which of them may reach the model, the five paths by which the answer could leak, and the guard and test that block each one.

**Author:** Diya Shrivastava · **Owning PR:** 5 (sections) · 6 (probes, continuous) · 7 (split, dedup) · 13 (retrieval) · 14 (gap report) · **Status:** Planned

**Related:** `architecture.md` §2, `data-flow.md`, design decisions D1, D2, D7, requirement NFR-01, risk R3.

---

## 1. The contract in one sentence

**Only the complaint and the insurer's position, from decisions dated earlier than the case being predicted, may ever be read by the classifier; the ombudsman's findings may be shown to the explainer, and the award may only become a label.**

---

## 2. The four sections

| # | Section | Example | Model input | Explainer | Label | Stored as |
|---|---|---|---|---|---|---|
| 1 | **Complaint / background** | "Hospitalised for 3 days; ₹1.2L claim repudiated for non-disclosure" | ✅ | ✅ | ❌ | part of `facts_text` |
| 2 | **Insurer's position** | "The insurer says the condition existed before inception" | ✅ | ✅ | ❌ | part of `facts_text` |
| 3 | **Findings / reasoning** | "I am satisfied the condition was not diagnosed before…" | ❌ **never** | ✅ precedents only | ❌ | `findings_text` |
| 4 | **Award / decision** | "I uphold this complaint and direct the insurer to pay…" | ❌ **never** | ❌ | ✅ only | `label`, `label_binary`; text discarded |

### Typical markers (learned per source and office in PR 5)

| Section | CIOINS | FOS | FSPO |
|---|---|---|---|
| Complaint | "Brief facts", "The complaint" | "The complaint", "What happened" | "Background", "The Complainant's Case" |
| Insurer | "The insurer's case", "Respondent's submission" | "The insurer said…" | "The Provider's Case" |
| Findings | "Observations", "Findings" | "What I've decided — and why" | "Analysis" |
| Award | "Award", "Order" | "My final decision" | "Decision" |

Marker lists live in `config.yaml`; the CIOINS row is a starting point and is extended per office as PR 5 finds new layouts.

### Boundary edge cases

| Case | Rule |
|---|---|
| Findings text appears before the findings marker (e.g. ombudsman comments inside the facts) | The sentence-level leak probe (§4, L1) flags it; the document is dropped or the rule tightened, never patched by hand |
| Insurer position quotes the ombudsman's earlier view (re-hearing) | Treated as findings; document dropped |
| FOS "provisional decision" quoted inside a final decision | Provisional reasoning counts as findings; cut from `facts_text` |
| Facts section missing | Document dropped (FR-05) |

---

## 3. Five leak paths

| # | Leak path | How the answer gets in | Guard | Where | Owning PR |
|---|---|---|---|---|---|
| **L1** | **Ombudsman reasoning in the input** | Segmenter puts findings or award sentences in `facts_text` | Section segmenter + sentence and n-gram leak probes | `parse/segment.py`, `tests/leak/` | 5, 6 |
| **L2** | **Outcome words in the facts** | Complainant writes "wrongly rejected", "unfair repudiation"; FOS background says "Mr X's complaint about the unfair decline" | Outcome-word lexicon: measured, reported, and optionally masked | `label/anonymise.py`, `tests/leak/` | 6 |
| **L3** | **Future data in training** | A random split lets the model see 2025 decisions while being tested on 2024 ones | Temporal split by `decision_date` | `dataset/split.py` | 7 |
| **L4** | **Same case in train and test** | One dispute published twice (re-issued award, provisional + final, office re-upload) lands in two splits | MinHash near-duplicate removal **before** splitting | `dataset/dedup.py` | 7 |
| **L5** | **Precedents from the future** | Retrieval returns a decision dated after the query, whose findings reveal how such cases now go | Date filter on every retrieval call | `retrieve/search.py` | 13 |

---

## 4. Guards and tests in detail

### L1 — Reasoning in the input

| Check | Rule | Fails when |
|---|---|---|
| Sentence probe | No normalised sentence of `findings` or `award` appears in `facts_text` of the same document | Any match |
| n-gram probe | No 13-gram (configurable) shared between `facts_text` and `findings` + `award` of the same document, ignoring quoted policy wording | Any match not on the policy-wording allowlist |
| Marker probe | No findings/award marker string from `config.yaml` appears inside `facts_text` | Any match |
| Hand check | 50 documents read section-by-section in PR 5 | < 95% correct |

The allowlist exists because both sides often quote the same policy clause; quoted clauses are not leakage.

### L2 — Outcome words in the facts

- Lexicon in `config.yaml`: *upheld, not upheld, allowed, dismissed, repudiation sustained, direct the insurer, award, wrongly, unfairly, unreasonably*, and similar.
- **Measured:** share of `facts_text` containing ≥ 1 lexicon term, per source and per label. A large difference between labels is reported as a leakage signal.
- **Ablation in PR 14:** results with lexicon terms masked vs not masked. If masking moves macro-F1 by more than the bootstrap CI, masking becomes the default.
- Not a hard CI failure, because complainants legitimately describe rejections as unfair; it is a reported metric.

### L3 — Future data in training

| Split | Rule |
|---|---|
| train | `decision_date` ≤ 2023-12-31 |
| val | 2024-01-01 ≤ `decision_date` ≤ 2024-12-31 |
| test | `decision_date` ≥ 2025-01-01 |

- Split fixed at build time and stored with the dataset version; never recomputed inside a training script.
- Calibrator and thresholds fitted on **val only**; a test asserts no test index is touched (FR-12).
- Baselines, fine-tuning and hyperparameter search never read `test.parquet`; only the report command does.

### L4 — Same case in two splits

- MinHash over shingled `facts_text`; Jaccard threshold in `config.yaml` (start at 0.8, tuned on a hand-checked sample).
- Dedup runs over **all** records before the split; for each near-duplicate cluster the **earliest** record is kept, so the survivor never moves to a later split.
- Post-split test: no pair across train/val/test exceeds the threshold (FR-08b).

### L5 — Precedents from the future

- Every call to `search()` requires a `before: date`. There is no default and no unfiltered method.
- Offline evaluation: `before` = the query document's own `decision_date`; the query document itself is excluded by `doc_id`.
- Live queries: `before` = today.
- Property test: random query dates, assert every returned precedent has `decision_date < before` (FR-15c).

---

## 5. Evidence that the contract holds

| Evidence | Expected if no leakage | Reported in |
|---|---|---|
| Leak-probe tests | 0 failures, on every PR from PR 6 | CI |
| Facts-only vs findings-included accuracy | Findings-included is **much** higher (findings contain the answer). A small gap means facts already contain the answer | `reports/` (PR 14) |
| Lexicon rate by label | Similar across labels | `reports/` (PR 14) |
| Accuracy far above published inter-annotator or baseline levels | Should not happen; investigate before celebrating | PR 11 description |

**Warning sign:** suspiciously high validation accuracy is treated as a leakage bug until proven otherwise (risk R3).

---

## 6. Test layout

```text
tests/leak/
├── test_sentence_probe.py     # L1: findings/award sentences not in facts_text
├── test_ngram_probe.py        # L1: shared n-grams, with policy-wording allowlist
├── test_marker_probe.py       # L1: no findings/award markers inside facts
├── test_lexicon_rate.py       # L2: computes and logs rate; fails only on schema
├── test_temporal_split.py     # L3: date ranges per split; calibrator uses val only
├── test_cross_split_dedup.py  # L4: no cross-split pair above threshold
└── test_retrieval_dates.py    # L5: property test on before-filter
```

All leak tests run in CI on every PR after PR 6 (NFR-01, continuous).
