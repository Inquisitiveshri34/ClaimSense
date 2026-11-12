# ClaimSense — Retrieval Rubric (Audit A5)

> How a human scores whether the precedents ClaimSense retrieves are about the same kind of dispute as the user's claim: the 40-case sample, what the reviewer sees, the exact judgment for each precedent, how the scores become topic match@5 and outcome agreement@5, and how the reviewer checks their own consistency.

**Author:** Diya Shrivastava · **Owning PR:** 13 (written before the sample is drawn) → 14 (scored) · **Status:** Planned

**Related:** `evaluation-protocol.md` §4 (E6, E6a), §5, §9, `../data/manual-audit-protocol.md` §7 (A5), `../modelling/retrieval-design.md` §7–§8, `../architecture/data-schema.md` §1 (`RejectionReason`), `faithfulness-rubric.md` (same 40 queries).

---

## 1. What this audit answers

Automatic proxies in `retrieval-design.md` §7 compare **dataset labels** (same `rejection_reason` column). They cannot tell whether two cases are about the same medical situation, or whether a person reading the precedent would find it relevant. A5 answers three questions a label match cannot:

1. **Same reason:** did the insurer reject both claims for the same kind of reason?
2. **Same condition:** are both about the same family of illness or treatment?
3. **Useful:** would a person with this claim learn something from this precedent?

Outcome agreement is computed mechanically from labels; it needs no judgment.

---

## 2. Sample

| Item | Value |
|---|---|
| Size | 40 test queries, 5 precedents each → **200 judgments** |
| Draw | `python -m claimsense.audit draw A5A6 --seed 2025` (shared with A6) |
| Population | Test records where `predict()` did not abstain |
| Strata | India ≥ 20 if available, rest split GB/IE by share; label-proportional within source; ≥ 5 true `partially_upheld` |
| Retrieval call | `predict(facts_text, query_date=decision_date, exclude_doc_id=doc_id)` with the shipped `config.yaml` |

The rubric below is committed **before** the draw. It is not changed after the sample is seen (`manual-audit-protocol.md` rule 4).

---

## 3. What the reviewer sees (and does not see)

| Shown | Hidden until scoring is done |
|---|---|
| Query `facts_text` (complaint + insurer position) | Query label |
| Each precedent's `facts_text` and `findings_text` excerpt | Precedent label, similarity score, rank |
| Each precedent's country and decision date | The system's predicted label |

Precedents are shown in **shuffled order** so rank does not suggest relevance. Labels are hidden because knowing a precedent was upheld makes it feel more or less relevant than it is.

---

## 4. Judgments per precedent

### R1 — Same rejection reason (`y` / `n` / `unclear`)

Read the insurer's stated reason in both texts and map each to one `RejectionReason` value:

| Value | Typical insurer wording |
|---|---|
| `non_disclosure` | pre-existing condition not declared, misrepresentation at proposal |
| `waiting_period` | initial 30-day, specific-disease or pre-existing-disease waiting period not completed |
| `exclusion` | permanent exclusion: cosmetic, experimental, self-inflicted, specified treatment |
| `not_medically_necessary` | hospitalisation not required, could be done as OPD, day care disputed |
| `documentation` | documents missing, late intimation, claim filed late, bills not original |
| `other` | sub-limits, room-rent proportionate deduction, network hospital issues, anything else |

- `y` if the query's **primary** reason equals any reason given in the precedent.
- `n` if they differ.
- `unclear` if either text does not state a reason. `unclear` is excluded from the denominator and counted.

Room-rent proportionate deduction is `other`, not `exclusion`, even though insurers sometimes describe it as one.

### R2 — Same condition family (`y` / `n` / `unknown`)

| Family | Examples |
|---|---|
| Cardiovascular | angioplasty, bypass, hypertension complications |
| Oncology | chemotherapy, radiotherapy, tumour surgery |
| Maternity and neonatal | delivery, complications of pregnancy, newborn care |
| Orthopaedic and injury | fracture, joint replacement, accident trauma |
| Ophthalmic | cataract, retinal procedures |
| Renal and urological | dialysis, kidney stones, prostate |
| Neurological | stroke, epilepsy, spine surgery |
| Mental health | psychiatric admission, de-addiction |
| Respiratory | pneumonia, asthma, COVID-19 |
| Gastro and hepatic | appendicitis, gall bladder, liver disease |
| Infectious (non-respiratory) | dengue, malaria, typhoid |
| Endocrine and diabetes | diabetes complications, thyroid |
| Dental | dental surgery |
| Cosmetic and elective | bariatric, cosmetic, fertility |
| Alternative systems | AYUSH treatment |
| Other | anything not above |

- `unknown` if either text names no condition (common in documentation disputes). Excluded from the denominator and counted.
- Use the condition the **claim** was for, not incidental history. A diabetic claiming for cataract surgery is Ophthalmic.

### R3 — Date check (mechanical)

The script fills `date_ok = decision_date < query_date`. Any `False` is a **bug** (E6a gate), not a score. Stop the audit, fix, redraw.

### R4 — Usefulness (`0` / `1` / `2`)

Imagine the person who wrote the query reading this precedent.

| Score | Meaning |
|---|---|
| **2** | Clearly informative: similar dispute, and the findings show how the ombudsman reasoned about it |
| **1** | Loosely related: same reason or same condition, but the reasoning would not transfer |
| **0** | Not helpful: different dispute, or the excerpt says nothing about the point at issue |

R4 is secondary. It is reported but has no target.

---

## 5. Metrics

For query *q* with scored precedents *P(q)* (excluding `unclear`/`unknown` for the relevant column):

| Metric | Formula | Target (`evaluation-protocol.md` E6) |
|---|---|---|
| **Reason match@5** | mean over *q* of share of *P(q)* with R1 = `y` | **≥ 0.60** |
| Condition match@5 | mean over *q* of share with R2 = `y` | Reported |
| **Topic match@5** | mean over *q* of share with R1 = `y` **and** R2 = `y` | Reported (headline in README) |
| **Hit@5** | share of queries with ≥ 1 precedent where R1 = `y` | **≥ 0.85** |
| Mean usefulness | mean R4 over all 200 | Reported |
| **Outcome agreement@5** | mean over *q* of share of precedents whose label equals the query's true label | Reported **beside chance** |
| Vote accuracy | share of queries where the majority precedent label equals the true label (ties → no vote) | Reported |
| Date correctness | share with `date_ok` | **100%** (gate) |

**Chance level for outcome agreement.** If precedents were picked at random from train, the expected agreement is Σ *p_c*², where *p_c* is the train share of each label. The report prints this next to outcome agreement@5 so a reader can see whether retrieval finds cases that went the same way more often than luck.

Outcome agreement is **not** expected to be near 1. Showing precedents that went the other way is part of an honest answer; the metric is there to describe retrieval, not to be maximised.

**CIs:** bootstrap over the 40 queries (1,000 resamples, seed 13), per `evaluation-protocol.md` §5.

---

## 6. Reviewer consistency

ClaimSense is a solo project, so there is no second annotator. Two checks stand in for one:

1. **Practice round.** Before scoring, score 5 **val** queries (not part of the sample) and re-read this rubric where you hesitated. Practice scores are not reported.
2. **Intra-rater check.** At least 7 days after finishing, re-score 8 randomly chosen queries (40 judgments) blind to your earlier answers. Report percent agreement and Cohen's κ for R1 and R2. If κ < 0.6 for either, note it as a limitation of the A5 numbers.

---

## 7. Edge cases

| Situation | Rule |
|---|---|
| Fewer than 5 precedents returned (similarity floor) | Score what is there; record `n_returned`. The query still counts once in each mean |
| Two reasons in the query | Primary = the reason the insurer leads with in its position |
| Precedent is a near-duplicate of the query | Should not happen (L4 dedup, `exclude_doc_id`). Log as a bug |
| Precedent excerpt is too short to judge | Open the full `findings_text`; if still unclear, R1/R2 = `unclear`/`unknown` |
| Different country, same dispute | Score normally; country is a slice, not a relevance criterion |

---

## 8. Scoring sheet and outputs

`reports/audits/A5-retrieval-<date>.csv`, one row per precedent:

```text
query_doc_id, query_source, precedent_doc_id, precedent_country, date_ok,
r1_same_reason, r2_same_condition, r4_useful, query_reason, precedent_reason,
query_condition_family, precedent_condition_family, note
```

Labels and ranks are joined in by the script **after** the sheet is locked:

```bash
python -m claimsense.audit score A5 reports/audits/A5-retrieval-<date>.csv
```

This writes `reports/audits/A5-summary.json` (all §5 metrics with CIs) which `evaluation-report.md` §5 reads. The row is also added to `audit_index.csv`.

### Worked example (invented)

> **Query:** Claim for cataract surgery rejected; insurer says the policy has a two-year waiting period for cataract and the policy is 14 months old.
>
> **Precedent A:** Cataract claim rejected under a 24-month specific-disease waiting period → R1 `y`, R2 `y`, R4 `2`.
> **Precedent B:** Knee replacement rejected under a pre-existing-disease waiting period → R1 `y`, R2 `n`, R4 `1`.
> **Precedent C:** Cataract claim cut by a sub-limit on lens cost → R1 `n` (`other`), R2 `y`, R4 `1`.
