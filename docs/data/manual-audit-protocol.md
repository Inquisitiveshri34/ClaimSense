# ClaimSense — Manual Audit Protocol

> One procedure for every hand check in the project: how a sample is drawn, how it is reviewed, how it is scored, where results are recorded and what happens when it fails. Hand checks are gates, so they must be repeatable and not quietly favourable.

**Author:** Diya Shrivastava · **Owning PR:** 5 (first use), reused in 6, 13, 15, 17 · **Status:** Planned

**Related:** `segmentation-rules.md` §6, `labelling-guide.md` §6, `anonymisation-spec.md` §6, `acceptance-criteria.md` (all Manual checks).

---

## 1. Audits covered

| Audit | Sample | Unit scored | Pass rule | PR | Detail |
|---|---|---|---|---|---|
| A1 Segmentation | 50 documents | Document (all 4 boundaries right) | ≥ 95% (≥ 48/50) | 5 | §3 |
| A2 Labels | 100 documents | Document label | ≥ 95% | 6 | §4 |
| A3 PII | 100 documents | Any remaining identifier | 0 hits | 6 | §5 |
| A4 Near-duplicate threshold | 60 candidate pairs | Pair (same case?) | Threshold chosen, precision reported | 7 | §6 |
| A5 Retrieval | 40 queries | Precedent topic match, outcome agreement | Reported (rubric) | 13 | §7 |
| A6 Explanation faithfulness | 40 cases | Sentence | Checker agreement ≥ 90% | 15 | §7 |
| A7 Plain language | 10 outputs | Output vs checklist | All items pass | 17 | NFR-12 |

---

## 2. General rules

1. **Seeded sampling.** Every sample is drawn by `python -m claimsense.audit draw <audit> --seed <n>`; the seed and the dataset/interim state hash are written into the audit file. Anyone can redraw the same sample.
2. **Stratified, not convenient.** Strata are fixed below before drawing. Never hand-pick "interesting" documents into a gated sample; add those to a separate, ungated *probe set*.
3. **Blind where possible.** For labels, the reviewer records their answer before seeing the system's. For segmentation, the reviewer sees boundaries (needed to judge them) but scores against the source PDF.
4. **Fixed rubric.** Each audit has its scoring sheet (§3–§7). The rubric is not changed after the sample is drawn.
5. **Fail → fix → fresh sample.** A failed gated audit is re-run on a **new** sample (new seed) after the fix. Re-scoring the same sample is allowed only for A2 to confirm a rule fix, and the fresh-sample result is the one reported.
6. **Record everything.** Results go to `reports/audits/<audit>-<date>.csv` plus a short summary pasted into the PR description (Definition of Done item 3). Sheets that show personal data (A3 before fixes) stay local and are not committed; commit only counts.
7. **Time-box.** Budget ≈ 2–3 minutes per segmentation doc, 1–2 per label, 4–5 per PII doc. If an audit runs far over budget, the documents are too long or the rubric too vague; note it.

---

## 3. A1 — Segmentation (50 documents)

**Population:** `data/interim/segments/` (retained documents) + 10% of dropped documents reviewed separately (were drops justified?).

| Stratum | Count |
|---|---|
| CIOINS, ≥ 5 different offices, ≥ 3 docs each | 25 |
| FOS | 12 |
| FSPO | 13 |

If CIOINS is not cleared yet (see `terms-of-use-audit.md`), redistribute to FOS/FSPO and record that the CIOINS part of A1 is pending.

**Scoring sheet:** `doc_id, marker_rule, complaint_ok, insurer_ok, findings_ok, award_ok, leak_in_facts (y/n), note`.

- A boundary is `ok` if it is within one sentence of the true boundary **and** no findings/award sentence sits in complaint/insurer.
- Any `leak_in_facts = y` makes the document incorrect regardless of other columns and is logged as an L1 bug.
- **Pass:** ≥ 48 of 50 documents with all four `ok`.

---

## 4. A2 — Labels (100 documents)

| Stratum | Count |
|---|---|
| CIOINS (free-text, highest risk) | 50 |
| FOS `Upheld` (partial detection risk) | 25 |
| FOS `Not upheld` | 5 |
| FSPO | 20 |

Within each stratum, sample proportionally to label, with at least 5 `partially_upheld` where available.

**Scoring sheet:** `doc_id, reviewer_label, reviewer_reason, system_label, system_reason, label_match, reason_match, error_type`.

`error_type` ∈ {`amount_parse`, `partial_missed`, `exclusion_missed`, `wrong_section`, `metadata_conflict`, `other`}.

**Pass:** label accuracy ≥ 95/100. Rejection-reason accuracy reported with a target of ≥ 85.

---

## 5. A3 — PII (100 documents)

**Population:** `data/processed/` candidate build (or `data/interim/labelled/` before PR 7).

| Stratum | Count |
|---|---|
| CIOINS | 60 |
| FOS | 20 |
| FSPO | 20 |

Within CIOINS, over-sample group mediclaim (employer names) and long documents (top length quartile).

**Procedure:** read `facts_text` and `findings_text` in full. Record every identifier still present with its entity code from `anonymisation-spec.md` §2. Also note over-removed tokens.

**Scoring sheet:** `doc_id, hits, hit_entities, over_removed, note`.

**Pass:** total hits = 0. Report over-removal count separately.

---

## 6. A4 — Near-duplicate threshold (60 pairs)

Draw 20 pairs each from Jaccard bands 0.6–0.7, 0.7–0.8, 0.8–0.9 (MinHash estimate). For each pair record `same_case (y/n)`. Choose the lowest threshold where precision of "same case" ≥ 0.9, record it in `config.yaml` → `dedup.threshold` and in `dataset-versioning.md`.

---

## 7. A5, A6 — Retrieval and explanations (40 cases)

Shared sample of 40 test queries, stratified by source (India ≥ 20 if available) and label.

| Audit | Per case record | Reported |
|---|---|---|
| A5 Retrieval | For each top-5 precedent: `same_rejection_reason (y/n)`, `same_condition_family (y/n)`, `outcome` | Topic match @5, outcome agreement @5 |
| A6 Faithfulness | For each explanation sentence: `supported_by_cited (y/n)`, compared to the NLI checker's verdict | Agreement with checker (gate ≥ 90%) |

---

## 8. Audit file layout

```text
reports/audits/
├── A1-segmentation-2026-xx-xx.csv
├── A2-labels-2026-xx-xx.csv
├── A3-pii-counts-2026-xx-xx.csv      # counts only; detailed sheet stays local
├── ...
└── audit_index.csv                   # audit, date, seed, state_hash, n, result, pass
```
