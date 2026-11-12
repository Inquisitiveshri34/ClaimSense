# ClaimSense — Faithfulness Rubric (Audit A6)

> How a human checks whether each sentence of a ClaimSense explanation is actually supported by the precedent it cites: the 40-case sample, what the reviewer sees, the label for every sentence, how dropped sentences are audited to catch an over-strict checker, and how the scores become the E7b and E7c gates.

**Author:** Diya Shrivastava · **Owning PR:** 13 (written before the sample is drawn) → 14 (scored) · **Status:** Planned

**Related:** `evaluation-protocol.md` §4 (E7a–E7c), §5, §9–§10, `../data/manual-audit-protocol.md` §7 (A6), `../modelling/citation-checking.md`, `../modelling/prompt-spec.md` (P-EX-v1), `../architecture/pipeline-interface.md` §2 (`ExplanationSentence`), `retrieval-rubric.md`, `../responsible-ai/responsible-use.md`.

---

## 1. What this audit answers

The citation checker (`citation-checking.md`) keeps a sentence only if an NLI model says its cited precedent entails it. That is an automatic judge, and automatic judges make mistakes. A6 measures two things:

1. **Is what users see true to the sources?** Of the sentences the checker **kept**, what share does a careful human agree are supported? (E7b, gate ≥ 0.90)
2. **Can the checker be trusted as a judge?** On kept **and** dropped sentences, how often does the human verdict match the checker's? (E7c, gate ≥ 0.90)

The structural rule (every shown sentence has at least one cite and every cite is a returned precedent, E7a) is checked automatically on all test queries, not here.

---

## 2. Sample

| Item | Value |
|---|---|
| Queries | The same 40 as A5 (`--seed 2025`), so retrieval and explanation can be read together |
| Kept sentences | **All** kept sentences of those 40 explanations |
| Dropped sentences | From `reports/explanations/dropped.jsonl` for those 40 queries: all, up to **40**, drawn with the same seed if more exist |
| Settings | Prompt `P-EX-v1`, shipped NLI model and threshold, `explain=True` |
| Empty explanations | Counted (`NO_SUPPORTED_EXPLANATION`), nothing to score |

Kept and dropped sentences are **mixed and shuffled** into one sheet with no indication of which is which.

---

## 3. What the reviewer sees (and does not see)

| Shown | Hidden until the sheet is locked |
|---|---|
| The sentence | Kept or dropped |
| Full `findings_text` of **each cited** precedent | NLI entailment and contradiction scores, drop code |
| The query's `facts_text` | Predicted label and probability |
| The other retrieved precedents (collapsed, open on demand) | |

The full findings text is shown, not the display excerpt, because the explainer read the full findings.

---

## 4. Judgments per sentence

### F1 — Support (one of four)

| Label | Meaning | Counts as `supported_by_cited` |
|---|---|---|
| **supported** | Every factual claim in the sentence is stated in, or follows directly from, the cited precedent(s) | `y` |
| **partially** | The main claim is supported, but a detail is added, stretched or wrong (a number, a time period, who decided) | `n` |
| **unsupported** | The cited precedent does not say this | `n` |
| **contradicted** | The cited precedent says the opposite | `n` |

**How to judge.** Split the sentence into its claims. Each claim must be findable in the cited text. Paraphrase is fine; inference beyond one obvious step is not. If a sentence cites two precedents, **each** cite must support the part it is attached to (matches `test_every_cite_must_support`).

### F2 — Attribution (`correct` / `misattributed` / `n/a`)

- `misattributed`: the claim is true of a **different** retrieved precedent, not the one cited. Counts as F1 `unsupported` for the gate, and is tallied separately because it suggests a prompt problem rather than invention.
- `n/a` when F1 is `supported`.

### F3 — Query fidelity (`ok` / `misstates`)

Sentences often link a precedent to the user ("As in your case, …"). `misstates` if the sentence gets the **query's** facts wrong (wrong condition, wrong reason, invented detail). This is a harm even when the precedent part is supported.

### F4 — Overgeneralisation (`y` / `n`)

`y` if the sentence turns one or a few precedents into a rule: "always", "never", "the ombudsman will", "insurers cannot". Report the rate; target 0.

### F5 — Advice or guarantee (`y` / `n`)

`y` if the sentence tells the user what to do, or promises an outcome ("you will win", "you should file immediately"). This breaks `responsible-use.md`. **Target 0**; any `y` is listed in the report verbatim with its query ID.

---

## 5. Judgments per explanation (40)

| Field | Values | Meaning |
|---|---|---|
| X1 label consistency | `consistent` / `mixed` / `opposite` | Does the explanation, read as a whole, argue for the predicted outcome? `opposite` means it argues for a different one. Judged after unhiding the predicted label |
| X2 counter-precedent hidden | `y` / `n` / `n/a` | Among the top 5, is there a precedent with the opposite outcome that is directly on point, and does the explanation leave it out while implying the cases agree? `n/a` if no such precedent |
| X3 readable | `y` / `n` | Could a non-lawyer follow it? Secondary |

---

## 6. Metrics

Let *K* = kept sentences scored, *D* = dropped sentences scored.

| Metric | Formula | Target |
|---|---|---|
| **Supported share (kept)** — E7b | # kept with F1 = supported / \|*K*\| | **≥ 0.90** (gate) |
| **Checker agreement** — E7c | # sentences in *K* ∪ *D* where (human `supported_by_cited` = `y`) equals (checker kept) / \|*K* ∪ *D*\| | **≥ 0.90** (gate) |
| False-drop rate | # dropped with F1 = supported / \|*D*\| | Reported: a high value means the checker is too strict and users lose good sentences |
| Partially / unsupported / contradicted shares | among *K* | Reported |
| Misattribution rate | # F2 = misattributed / \|*K*\| | Reported |
| Query misstatement rate | # F3 = misstates / \|*K*\| | Reported; target 0 |
| Overgeneralisation rate | # F4 = y / \|*K*\| | Reported; target 0 |
| **Advice/guarantee count** | # F5 = y | **0** (any non-zero is listed) |
| Label consistency | share of X1 = consistent | Reported |
| Hidden counter-precedent | share of X2 = y among applicable | Reported |
| Empty explanation rate | # empty / 40 | Reported |

Because the dropped set is capped at 40 and kept sentences are not, checker agreement is reported **both** pooled (gate) and separately for *K* and *D*, so a reader can see which side the errors come from.

**CIs:** cluster bootstrap over the 40 **queries** (all sentences of a query resampled together), 1,000 resamples, seed 13. Sentences from one explanation share a prompt and precedents, so treating them as independent would make CIs too narrow.

---

## 7. If a gate fails

Following `evaluation-protocol.md` §10 and `manual-audit-protocol.md` rule 5:

1. Read the failures by category. Many `partially` → tighten the prompt's "only state what the precedent says" rule (new prompt version). Many false drops → the NLI threshold is too strict. Many `unsupported` kept → too loose.
2. Change the threshold or prompt using a **val** dev set of 20 queries, never these 40.
3. Draw a **fresh** A6 sample (new seed, same strata) from test and score it.
4. Report both: the failed first result and the fresh result. The fresh one decides the gate.

---

## 8. Reviewer consistency

- **Practice round:** 3 val explanations before starting; not reported.
- **Intra-rater check:** ≥ 7 days later, re-score 20 sentences blind. Report agreement and κ on `supported_by_cited`. κ < 0.6 is noted as a limitation.
- **Time-box:** about 1–2 minutes per sentence. Long overruns mean the cited findings are too long to judge fairly; note it.

---

## 9. Scoring sheet and outputs

`reports/audits/A6-faithfulness-<date>.csv`, one row per sentence:

```text
query_doc_id, sentence_id, sentence, cites, f1_support, f2_attribution,
f3_query_fidelity, f4_overgeneral, f5_advice, note
```

`reports/audits/A6-explanations-<date>.csv`, one row per query:

```text
query_doc_id, n_kept, n_dropped_scored, x1_label_consistency, x2_counter_hidden, x3_readable, note
```

```bash
python -m claimsense.audit score A6 reports/audits/A6-faithfulness-<date>.csv
```

joins in `kept/dropped`, NLI scores and drop codes after the sheet is locked and writes `reports/audits/A6-summary.json` for `evaluation-report.md` §6. Disagreements between human and checker are also written to `reports/audits/A6-disagreements.csv`; PR 15 reads it for `error-taxonomy.md` §5.

### Worked example (invented)

> **Cited precedent:** "The complainant had undergone thyroid treatment in 2019, which was not declared in the proposal form. The Ombudsman found that the non-disclosed condition was unrelated to the cardiac admission and directed the insurer to pay the claim."
>
> | Sentence | F1 | Why |
> |---|---|---|
> | "In a similar case, the ombudsman held that an undisclosed condition unrelated to the treatment claimed did not justify rejection [P1]." | supported | Both parts are in the text |
> | "The ombudsman ordered the insurer to pay the full amount with interest [P1]." | partially | Payment is supported; "full amount with interest" is not stated |
> | "Non-disclosure rejections are usually overturned [P1]." | unsupported, F4 = y | One case does not support "usually" |
