# ClaimSense — Prompt Specification

> Every LLM prompt ClaimSense uses, written out in full and versioned like code: the zero-shot classification baseline and the cited explanation prompt, with the model, decoding settings, input assembly, output format, caching and change rules. A prompt is part of the model; if it changes silently, the reported results stop being reproducible.

**Author:** Diya Shrivastava · **Owning PR:** 10 (P-ZS-v1) · 13 (P-EX-v1) · **Status:** Planned

**Related:** FR-10, FR-16, design decision D6, NFR-05, risks R10, R11, `baselines.md` (B5), `citation-checking.md`, `retrieval-design.md`, `../architecture/pipeline-interface.md` §6.

---

## 1. Rules

1. **Every prompt has an ID** of the form `P-<PURPOSE>-v<N>`, stored as one file in `src/claimsense/prompts/<id>.yaml`.
2. **A version is frozen** the first time it produces a number that appears in a PR description or report. Any change after that (wording, model, decoding setting, input assembly) creates `v<N+1>`.
3. **Every LLM-backed run logs** `prompt_id`, the prompt file's SHA-256, the provider and the exact model ID (`experiment-log.md` §3).
4. **Only anonymised dataset text is ever sent** to the provider (`facts_text`, `findings_text`). In the live app the user's own facts are also sent; the app says so next to the input box.
5. **Temperature 0** for everything; ClaimSense needs repeatable output, not variety.

---

## 2. Registry

| ID | Purpose | Used by | PR | Status |
|---|---|---|---|---|
| **P-ZS-v1** | Zero-shot outcome classification | Baseline B5 | 10 | Planned |
| **P-EX-v1** | Cited plain-language explanation | `explain/generate.py` | 13 | Planned |

The topic check (`abstention-policy.md` §5) uses keywords and a small classifier, not an LLM, so it has no prompt.

---

## 3. Provider, model and decoding

```yaml
llm:
  provider: groq             # alternative: gemini
  model: <exact model ID>    # pinned when PR 10 opens; copy the ID string exactly
  model_checked_on: <date>   # when the ID was confirmed available on the provider
  temperature: 0
  top_p: 1
  seed: 13                   # sent only if the provider supports it
  response_format: json      # use the provider's JSON mode where available
  timeout_s: 20
  retries: 2                 # explain.retries in pipeline-interface.md
  max_output_tokens:
    P-ZS: 200
    P-EX: 400
```

| Item to record at PR 10 | Value |
|---|---|
| Provider | |
| Model ID | |
| Context window | |
| Free-tier rate limits | |
| Data-retention terms (do they train on inputs?) | |
| Link to the terms page | |

**Model deprecation:** hosted models are retired over time. If the pinned model disappears, the replacement is a **new prompt version** (same text, new model), and B5 and the explanation metrics are re-run under it. Old results keep their old version label.

Choose an instruction-tuned model from the provider's current list, in the 8 B–70 B range, that supports JSON output. Prefer the same model for P-ZS and P-EX so the provider terms are checked once.

---

## 4. P-ZS-v1 — zero-shot classification (baseline B5)

### Inputs

| Placeholder | Source |
|---|---|
| `{facts}` | `facts_text`, truncated to 6,000 characters (head 4,500 + tail 1,500) |

### System message

```text
You are assessing health-insurance complaints decided by an insurance ombudsman.
You will read the complainant's account and the insurer's stated position.
You do not see the ombudsman's reasoning or decision.

Predict how the ombudsman most likely ruled, using exactly one of:
- "upheld": the insurer was told to pay the claim in full or substantially.
- "partially_upheld": the insurer was told to pay part of the claim.
- "rejected": the insurer's decision was confirmed; nothing to pay.

Give a probability for each of the three outcomes; they must add up to 1.
Respond with JSON only, in this exact shape:
{"label": "<one of the three>", "probabilities": {"upheld": 0.0, "partially_upheld": 0.0, "rejected": 0.0}}
```

### User message

```text
Complaint and insurer's position:
"""
{facts}
"""
```

### Parsing

1. Parse JSON; on failure, extract the first `{...}` block and retry parsing.
2. `label` must be one of the three values; probabilities must be numbers ≥ 0.
3. Renormalise probabilities to sum to 1; if they are all zero, use 1.0 on `label`.
4. If `label` disagrees with the arg-max probability, use the arg-max (logged as `label_prob_mismatch`).
5. Still unparseable after one retry call → train majority class, counted in `parse_failures` (`baselines.md` §3).

No reason field is requested: free-text reasons add tokens and nothing B5 is scored on.

---

## 5. P-EX-v1 — cited explanation

### Inputs

| Placeholder | Source |
|---|---|
| `{facts}` | The user's facts (or the test record's `facts_text` offline), truncated as in P-ZS |
| `{outcome_words}` | Predicted label in words: "upheld", "partly upheld", "not upheld" |
| `{precedents}` | The k retrieved precedents, rendered as below |

Each precedent is rendered with a **local tag** `P1 … Pk`; code maps tags back to `doc_id`s after generation, so the model never sees or invents real IDs.

```text
[P1] Country: India | Year: 2024 | Outcome: upheld | Insurer's reason: non-disclosure
Findings excerpt:
"""
{findings_excerpt}
"""
```

### Findings excerpt selection

The citation checker judges each sentence against **exactly the text the explainer saw**, so the excerpt is fixed here:

1. Split the precedent's `findings_text` into windows of about 600 characters at sentence boundaries.
2. Embed the windows with the retrieval encoder and score them against the query embedding.
3. Keep the **two best windows**, in their original order, joined with " … " (≤ 1,200 characters).

The same excerpt is stored in `Precedent.findings_excerpt` and shown in the app.

### System message

```text
You explain, in plain English, how an insurance ombudsman decided earlier cases that
resemble a person's rejected health-insurance claim.

Rules:
1. Use ONLY the findings excerpts provided. Do not use outside knowledge about law,
   insurance or medicine.
2. Write at most 5 sentences. Each sentence must describe what the ombudsman found
   in one or more of the given cases, and must cite them with their tags, e.g. [P2].
   Only cite a case whose excerpt directly supports the sentence.
3. Do not tell the person what to do, do not promise an outcome, and do not say
   their claim will succeed or fail.
4. Use simple words. Explain any insurance term you use (for example, "waiting period").
5. If the excerpts do not support any useful sentence, return an empty list.

Respond with JSON only, in this exact shape:
{"sentences": [{"text": "<one sentence>", "cites": ["P1"]}]}
```

### User message

```text
The person's situation:
"""
{facts}
"""

Our model estimates that cases like this were most often {outcome_words}.
Explain what the ombudsman focused on in these earlier cases.

Earlier cases:
{precedents}
```

### Why the predicted outcome is included

Without it, the explanation might describe precedents that point the other way and contradict the prediction shown above it. With it, the explainer is asked what similar cases turned on, not to justify the label; the citation check still drops anything the excerpts do not support.

### Parsing

| Problem | Handling |
|---|---|
| Invalid JSON | One retry call; then `explanation = []`, warning `NO_SUPPORTED_EXPLANATION` |
| Inline tags left in `text` ("… [P2].") | Stripped from `text`; merged into `cites` |
| Tag not in `P1…Pk` | That cite removed; sentence goes to the checker with remaining cites |
| More than 5 sentences | First 5 kept |

The checks after parsing are in `citation-checking.md`.

---

## 6. Caching

```text
key   = sha256(prompt_id | prompt_file_sha | provider | model | decoding params | rendered messages)
store = data/cache/llm/<prompt_id>.jsonl      # git-ignored; one line per call: key, response, created_at
```

- Evaluation always reads the cache first, so re-running the report costs no API calls (R11).
- Live app calls are **not** cached to disk, because the user's facts must not be stored (`pipeline-interface.md` §1).
- Clearing the cache never changes results at temperature 0 except where the provider is non-deterministic; any drift is measured once in PR 14 by re-calling 50 cached items.

---

## 7. Token budget

| Prompt | Input (approx.) | Output |
|---|---|---|
| P-ZS-v1 | System ~200 + facts ≤ ~1,500 tokens | ≤ 200 |
| P-EX-v1 | System ~250 + facts ≤ ~1,500 + 5 precedents × ~350 ≈ 3,500 tokens | ≤ 400 |

A test renders both prompts on the longest fixture and asserts the total stays under 60% of the pinned model's context window.

---

## 8. Tests

| Test | Checks |
|---|---|
| `test_prompt_files_hashed` | Every prompt file's hash matches the registry; a changed file without a version bump fails CI |
| `test_render_zs` / `test_render_ex` | Templates render with fixtures; no unfilled `{placeholders}` |
| `test_ex_tags_map_to_doc_ids` | `P1…Pk` map back to the right `doc_id`s; unknown tags are dropped |
| `test_ex_no_query_findings` | Offline, the query record's own findings never appear in the precedent block (L1, L5) |
| `test_parsers` | Valid, malformed, extra-text and empty responses handled as in §4 and §5 |
| `test_token_budget` | Longest fixture fits the budget in §7 |

---

## 9. Change log

| Version | Date | Change | Reason | Results affected |
|---|---|---|---|---|
| P-ZS-v1 | | Initial | — | B5 |
| P-EX-v1 | | Initial | — | Explanation metrics, A6 |
