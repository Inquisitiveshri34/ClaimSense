# ClaimSense — Baselines

> The five models every ClaimSense classifier must beat, with their exact configurations. A baseline is only useful if it is fitted as carefully as the main model, so each one gets the same input, the same split discipline, the same tuning budget rules and the same metrics.

**Author:** Diya Shrivastava · **Owning PR:** 9 (majority, rules, TF-IDF + LR) · 10 (embeddings + LR, zero-shot LLM) · **Status:** Planned

**Related:** FR-10, design decision D4, `../05-project-description.md` §7.2, `finetuning-spec.md`, `experiment-log.md`, `prompt-spec.md` (P-ZS-v1), `../architecture/leakage-contract.md` (L3).

---

## 1. Purpose

| Baseline | Question it answers |
|---|---|
| **B1 Majority class** | What does "knowing nothing" score? |
| **B2 Rejection-reason rules** | Does the insurer's stated reason alone predict the outcome? |
| **B3 TF-IDF + logistic regression** | How far do word counts get? (The headline comparison in `05` §7.1.) |
| **B4 Embeddings + logistic regression** | Do semantic features add anything over word counts? |
| **B5 Zero-shot LLM** | Is fine-tuning worth it compared with simply prompting a large model? |

If the fine-tuned model in PR 11 does not beat all five on validation, that is reported as a finding (risk R8), not hidden.

---

## 2. Shared rules (all five)

| Rule | Value |
|---|---|
| **Input** | `facts_text` only (complaint + insurer position). Never `findings_text`, never award text (L1). |
| **Fit on** | `train` split |
| **Tune on** | `val` split: hyperparameters chosen by **val macro-F1** |
| **Test split** | Never read in PR 9 or 10. Test scores are produced only by the report command in PR 14 (L3). |
| **Labels** | 3 classes: `upheld`, `partially_upheld`, `rejected` |
| **Class imbalance** | `class_weight="balanced"` where the estimator supports it (R7) |
| **Seeds** | `13` for all stochastic steps; B5 uses temperature 0 |
| **Dataset** | The frozen version in `data/processed/LATEST`; its hash is logged with every run |
| **Logging** | Every run goes to the tracker (`experiment-log.md`) with config, metrics and val predictions |

### Metrics (computed by one shared function)

All baselines and later models are scored by `claimsense.eval.metrics.score(y_true, proba)` so no model gets a friendlier metric.

| Metric | Definition | Role |
|---|---|---|
| **Macro-F1** (3-class) | Unweighted mean of per-class F1 | **Primary**; decides "beats" |
| Per-class F1 | F1 for each label | Shows whether `partially_upheld` is ignored |
| **PR-AUC, any payment** | Average precision with score = P(upheld) + P(partially upheld), positive = `label_binary` | Required by FR-10 notes; reported with base rate |
| Accuracy | Share correct | Context only |
| ECE, Brier | See `calibration.md` §4 | Reported for comparison; not gated for baselines |
| 95% CI | Bootstrap, 1,000 resamples of val records | Every macro-F1 and PR-AUC |

---

## 3. Configurations

All configs live under `baselines:` in `config.yaml`; the values below are the defaults committed in PR 9/10.

### B1 — Majority class `[PR 9]`

```yaml
b1_majority:
  estimator: sklearn.dummy.DummyClassifier
  strategy: prior        # predicts the most frequent class; probabilities = train class shares
```

- With `prior`, every record gets the same score, so PR-AUC equals the positive base rate. That is the floor.
- Macro-F1 will be low by design (one class gets all predictions).

### B2 — Rejection-reason rules `[PR 9]`

A lookup table, not a learned model:

```yaml
b2_rules:
  keys: [rejection_reason, source]   # most specific cell first
  backoff: [[rejection_reason], []]  # then reason only, then global prior
  min_cell_n: 20                     # back off when a cell has fewer train records
  smoothing_alpha: 1.0               # Laplace smoothing on label counts
```

1. For each `(rejection_reason, source)` cell, count train labels and add `alpha` to each class.
2. If the cell has fewer than `min_cell_n` records, use the `rejection_reason` cell; if that is also small, use the global prior.
3. Predicted probabilities are the smoothed shares; predicted label is the arg-max.

> **Caveat to state in the report.** B2 uses the dataset's `rejection_reason` column, which was extracted by the labeller from the insurer's position. A live user does not supply this field, so B2 is slightly optimistic compared with a text model that must infer the reason itself. This makes it a *stronger* baseline, which is acceptable.

### B3 — TF-IDF + logistic regression `[PR 9]`

```yaml
b3_tfidf_lr:
  vectorizer:
    analyzer: word
    ngram_range: [1, 2]
    min_df: 3
    max_df: 0.9
    max_features: 50000
    sublinear_tf: true
    lowercase: true
    strip_accents: unicode
    token_pattern: "(?u)\\b\\w\\w+\\b|\\[[A-Z]+\\]"   # keeps anonymiser tokens like [PERSON] as single tokens
  classifier:
    estimator: sklearn.linear_model.LogisticRegression
    solver: saga
    max_iter: 3000
    class_weight: balanced
    C_grid: [0.1, 0.3, 1.0, 3.0, 10.0]
```

- The vectorizer is fitted on train only; val is transformed with the fitted vocabulary.
- Pick the `C` with the best val macro-F1; ties → smaller `C` (simpler model).
- Save the top 30 positive and negative weights per class to `reports/baselines/b3_top_terms.csv`. Outcome words such as *wrongly* or *unfair* near the top are an L2 signal to note in the PR description.

### B4 — Sentence embeddings + logistic regression `[PR 10]`

```yaml
b4_embed_lr:
  encoder: BAAI/bge-small-en-v1.5     # same encoder as retrieval (retrieval-design.md §3)
  pooling: chunk_mean                 # 400-token windows, 50-token overlap, mean of normalised chunk vectors
  normalize: true
  cache_dir: data/cache/emb/          # <encoder>/<dataset_version>.npy
  classifier:
    estimator: sklearn.linear_model.LogisticRegression
    solver: lbfgs
    max_iter: 3000
    class_weight: balanced
    C_grid: [0.1, 0.3, 1.0, 3.0, 10.0]
```

- Using the retrieval encoder means one embedding pass serves both B4 and the precedent index. If PR 13 changes the encoder, B4 is re-run and logged as a new row.
- Embeddings are cached per dataset version so re-runs cost no GPU.
- **Done-when (PR 10):** B4 beats B3 on val macro-F1, or the PR description explains the gap. Embeddings often lose to TF-IDF on long, domain-specific text; that is a valid result.

### B5 — Zero-shot LLM `[PR 10]`

```yaml
b5_zero_shot:
  prompt_id: P-ZS-v1        # prompt-spec.md §4
  provider: groq            # or gemini; same provider as the explainer
  model: <pinned model ID>  # recorded in prompt-spec.md §3 when PR 10 is opened
  temperature: 0
  max_output_tokens: 200
  retries_on_parse_error: 1
  cache: data/cache/llm/
  run_on: [val]             # test only via the PR 14 report command
```

- The prompt asks for a JSON label plus a probability for each class (verbalised probabilities). These are used for PR-AUC and ECE, and are expected to be poorly calibrated; that is part of what the baseline shows.
- **Parse failures:** after one retry, the record is assigned the train majority class and counted in `parse_failures`. The count is reported; a rate above 2% means the prompt needs a new version.
- **Privacy:** only anonymised `facts_text` is sent to the provider. Check the provider's data-retention terms at PR 10 and note them in `prompt-spec.md` §3.
- **Cost control:** every call is cached by input hash (`prompt-spec.md` §6), so re-running the evaluation never re-calls the API (risk R11).

---

## 4. Results (filled in by PRs 9–10)

Validation split, dataset version `v________`.

| ID | Baseline | Macro-F1 [95% CI] | F1 upheld / partial / rejected | PR-AUC any payment (base rate) | Accuracy | Run ID |
|---|---|---|---|---|---|---|
| B1 | Majority class | | | | | |
| B2 | Rejection-reason rules | | | | | |
| B3 | TF-IDF + LR | | | | | |
| B4 | Embeddings + LR | | | | | |
| B5 | Zero-shot LLM | | | | | |

**Best baseline on val macro-F1:** ______ → this is the bar PR 11 must clear.

---

## 5. The bar for later PRs

| Check | Where | Rule |
|---|---|---|
| Fine-tuned model beats every baseline | PR 11, val | Higher val macro-F1 than **each** of B1–B5 (mean over 3 seeds, `finetuning-spec.md` §7) |
| Headline claim | PR 14, test | Fine-tuned vs **B3**: bootstrap 95% CIs on test macro-F1 do not overlap (`05` §7.1) |
| Value of fine-tuning | PR 14, test | Fine-tuned vs **B5** reported with CIs |
| If the bar is not met | PR 11 | Report honestly, analyse why, ship the strongest model as the production classifier (R8) |

---

## 6. Code and tests

```text
src/claimsense/models/baselines.py    # build_b1() … build_b5(), fit(), predict_proba()
models/baselines/<id>.joblib          # fitted B1–B4 + meta.json (run ID, dataset version)
reports/baselines/                    # val predictions, top terms, confusion matrices
tests/test_baselines.py
```

| Test | Checks |
|---|---|
| `test_baselines_fit_fixture` | Each of B1–B4 fits and predicts on a 60-row fixture; probabilities sum to 1 |
| `test_baselines_no_test_split` | Loading code raises if asked for `test` outside the report command (L3) |
| `test_baselines_deterministic` | Two fits with seed 13 give identical val predictions |
| `test_b2_backoff` | Small cells fall back to reason-only, then global prior |
| `test_b5_parser` | Valid, malformed and partial JSON responses map to the right label or a counted failure |
