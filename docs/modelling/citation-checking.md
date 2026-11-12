# ClaimSense — Citation Checking

> How ClaimSense makes sure every explanation sentence is supported by the precedent it cites: the structural checks, the NLI model that judges support, the threshold and how it is chosen, the exact drop rule, and how the checker itself is audited.

**Author:** Diya Shrivastava · **Owning PR:** 13 (checker) · 15 (faithfulness audit A6) · **Status:** Planned

**Related:** FR-16, NFR-04, design decision D6, risk R10, `prompt-spec.md` §5, `retrieval-design.md`, `../architecture/pipeline-interface.md` §2–§4, `../data/manual-audit-protocol.md` §7 (A6).

---

## 1. Purpose

LLMs write fluent sentences that sound grounded but are not. The explainer is told to cite only supporting precedents (`prompt-spec.md` §5), but instructions are not guarantees. The citation checker is the guarantee: **a sentence reaches the user only if an independent model agrees that its cited precedents support it** (FR-16). Unsupported sentences are removed, never rewritten.

---

## 2. Where it runs

```text
explainer JSON → parse (prompt-spec §5) → structural checks (§3) → NLI support check (§4) → drop rule (§5) → ExplanationSentence list
```

It runs only when no abstain code has fired (`pipeline-interface.md` §4, step 7).

---

## 3. Structural checks (no model needed)

Applied first, in order. A sentence that fails one is dropped with the reason code shown.

| # | Check | Drop code |
|---|---|---|
| S1 | Sentence text is non-empty after removing tags and whitespace | `EMPTY` |
| S2 | Has at least one cite | `NO_CITE` |
| S3 | Every cite tag maps to a retrieved precedent (`P1…Pk`); unknown tags are removed, and if none remain the sentence is dropped | `UNKNOWN_CITE` |
| S4 | Contains no advice or promise phrase from the lexicon in `config.yaml` (`you should`, `you will win`, `you will get`, `guaranteed`, `definitely`, `we recommend`, `file a complaint`, …) | `ADVICE_PHRASE` |
| S5 | Is a single sentence (one terminal punctuation mark, after removing abbreviations); longer text is split and each part re-checked | — |

S4 enforces "not legal advice" (R12) at the sentence level, independent of the prompt.

---

## 4. NLI support check

### Model

| Item | Value |
|---|---|
| Model | `cross-encoder/nli-deberta-v3-base` (`cite_check.model`) |
| Output | Scores for contradiction / entailment / neutral, turned into probabilities with softmax |
| Label order | Read from the model's `config.id2label` at load time; **never hard-coded** |
| Device | CPU |

### Premise and hypothesis

| Role | Text |
|---|---|
| **Premise** | The cited precedent's `findings_excerpt`: exactly the ≤ 1,200-character excerpt the explainer saw (`prompt-spec.md` §5) |
| **Hypothesis** | The sentence text with cite tags removed |

Using the same excerpt the explainer saw means support is judged on the evidence actually given. The excerpt fits within the model's 512-token input with room for the hypothesis; if a pair is longer, the premise is truncated from the end and the event is logged.

### Scores per cite

For each (sentence, cited precedent) pair:

- `entail` = P(entailment)
- `contra` = P(contradiction)

---

## 5. Drop rule

A sentence is **kept** only if, for **every** precedent it cites:

```text
entail ≥ cite_check.min_entailment     (start 0.70)
and
contra < cite_check.max_contradiction  (start 0.50)
```

Otherwise the whole sentence is dropped (`LOW_ENTAILMENT` or `CONTRADICTION`).

| Choice | Alternative rejected | Why |
|---|---|---|
| Every cite must support the sentence | Keep the sentence if any one cite supports it and silently remove the others | A sentence like "In both cases the ombudsman…" claims support from both; partial support is not support |
| Drop, never edit | Rewrite the sentence to fit the evidence | Rewriting is another unverified generation |
| Explicit contradiction check | Entailment threshold alone | A sentence can score moderate entailment and moderate contradiction on a mixed excerpt; contradiction is the more harmful error |

`ExplanationSentence.support_score` = the **minimum** `entail` over its cites (the weakest link).

If no sentence survives: `explanation = []` and warning `NO_SUPPORTED_EXPLANATION`. The prediction still stands (FR-16c, `pipeline-interface.md` §3).

---

## 6. Choosing the thresholds

The thresholds are chosen on a **dev set** that is separate from the A6 audit, so the audit stays an honest test of the checker.

| Set | Size | Split | Use |
|---|---|---|---|
| **Dev set** | 30 queries | `val` | Tune `min_entailment` and `max_contradiction` |
| **A6 audit set** | 40 queries | `test` | Measure checker agreement with a human (gate) |

### Procedure

1. Run the explainer on the 30 dev queries **without** the NLI filter (structural checks only).
2. Hand-label each (sentence, cite) pair: `supported` / `not supported`, blind to the NLI scores.
3. Sweep `min_entailment` from 0.50 to 0.95 in steps of 0.05.
4. **Pick the lowest threshold where precision of kept pairs ≥ 0.95** (at least 95% of what the checker keeps is truly supported).
5. Report recall at that threshold (share of truly supported sentences kept). Low recall means more empty explanations, not wrong ones, which is the right direction for errors.
6. Set `max_contradiction` the same way only if contradictions occur in the dev set; otherwise keep 0.50.

The rule in step 4 is fixed before the dev set is labelled.

---

## 7. Metrics

| Metric | Definition | Target / role | PR |
|---|---|---|---|
| Pre-filter support rate | Share of generated sentences a human marks supported (dev set) | Shows how often the explainer invents; reported | 13 |
| Post-filter citation rate | Share of shown sentences with ≥ 1 valid cite | **100%** by construction (FR-16) | 13 |
| **Checker agreement (A6)** | Share of sentences where the human verdict equals the checker's keep/drop verdict, on 40 test cases | **≥ 90%** (NFR-04) | 15 |
| Kept-sentence precision (A6) | Of kept sentences, share a human marks supported | Reported; the number users effectively experience | 15 |
| Drop rate by code | `NO_CITE`, `UNKNOWN_CITE`, `ADVICE_PHRASE`, `LOW_ENTAILMENT`, `CONTRADICTION` | Reported; feeds PR 15 error analysis | 13, 15 |
| Empty-explanation rate | Share of answered queries with `explanation = []` | Reported; high values mean k or the prompt needs work | 13, 16 |

---

## 8. Known limitations

- **Generalisation sentences.** "In similar cases, the ombudsman required proof of an earlier diagnosis" summarises rather than restates; NLI may score it as neutral. The prompt asks for sentences about what the cited cases found, which helps. The dev set shows how often good sentences are lost this way.
- **Anonymiser tokens.** Excerpts contain `[PERSON]`, `[PROVIDER]` and similar; the explainer is told to avoid them. Sentences containing them are not dropped, but are counted.
- **NLI is not a lawyer.** It checks that a sentence follows from the text, not that the ombudsman's reasoning was correct or applies to the user. The disclaimer covers this.
- **Language.** English only, matching `UNSUPPORTED_LANGUAGE`.

---

## 9. Latency (part of NFR-06's 10 s)

At most 5 sentences × k cites. With typical 1–2 cites per sentence, that is ≈ 5–10 NLI pairs, batched in one forward pass on CPU.

| Step | Budget |
|---|---|
| Structural checks | negligible |
| NLI batch (≤ 10 pairs) | ≤ 1.5 s |

If the budget is exceeded, reduce `explain.max_sentences` before touching the threshold.

---

## 10. Logging

Each dropped sentence is logged (offline evaluation only, never in the live app) to `reports/explanations/dropped.jsonl`:

```json
{"query_doc_id": "…", "sentence": "…", "cites": ["fos-2022-…"], "drop_code": "LOW_ENTAILMENT", "entail": [0.41], "contra": [0.12], "prompt_id": "P-EX-v1"}
```

PR 15 reads this file to categorise explanation failures.

---

## 11. Code and tests

```text
src/claimsense/explain/cite_check.py   # check(sentences, precedents) -> list[ExplanationSentence], list[Dropped]
```

| Test | Checks |
|---|---|
| `test_structural_checks` | Each of S1–S5 drops or keeps the right fixture sentences with the right code |
| `test_every_cite_must_support` | Two-cite sentence with one weak cite is dropped |
| `test_contradiction_drop` | High-contradiction pair is dropped even with entailment above threshold |
| `test_label_order_from_config` | Entailment index is taken from `id2label`, verified on a known entailment pair |
| `test_empty_is_warning` | No surviving sentences → `explanation == []` and `NO_SUPPORTED_EXPLANATION` in warnings, `abstain is False` |
| `test_cites_in_precedents` | Every output cite is a `doc_id` in the returned precedents (FR-16) |
