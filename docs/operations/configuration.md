# ClaimSense — Configuration

> Every setting ClaimSense reads: the full `config.yaml` with each key's meaning, starting value, which PR tunes it and whether changing it forces a new dataset version or a retrain; the environment variables (including the Groq and Gemini API keys); and the rules for where a value may live. One file holds every number, so code, tests and reports cannot drift apart.

**Author:** Diya Shrivastava · **Owning PR:** 1 (loader, schema, `.env.example`); keys added by the PR that first uses them · **Status:** Planned

**Related:** NFR-05, NFR-08, `setup.md`, `ci-cd.md`, `../testing/test-strategy.md` §1 (principle 4), `../pipeline-interface.md` §6, `../data/collection-runbook.md` §2, `../data/dataset-versioning.md` §2, `../modelling/finetuning-spec.md` §4–§5, `../modelling/calibration.md`, `../modelling/retrieval-design.md` §4, `../modelling/abstention-policy.md` §3, §5, `../modelling/prompt-spec.md` §3, `../modelling/citation-checking.md`, `../evaluation-protocol.md` §5.

---

## 1. Rules

1. **One source of truth.** Every threshold, seed, path and model ID lives in `config.yaml`. Code and tests read it through `claimsense.config.load()`; no number is copied into a module or a test file.
2. **No secrets in `config.yaml`.** API keys, tokens and anything personal come from environment variables (§5). `config.yaml` is committed and printed into run logs.
3. **Validated at load.** `config.yaml` is parsed into a Pydantic model (`src/claimsense/config.py`). Unknown keys, wrong types and out-of-range values fail at start-up, not mid-run.
4. **Tuned values are written back with evidence.** When a PR tunes a starting value (for example `abstain.threshold`), it changes `config.yaml` **and** the matching artefact (`models/thresholds.json`), and the PR description records the evidence. A mismatch between the two raises at load.
5. **Changes that touch data force a new version.** Keys marked **V** in §3 are part of the dataset `config_hash` (`dataset-versioning.md` §2); changing one means a new `dataset_version`.
6. **Changes that touch a model force a retrain or refit.** Keys marked **M** change the classifier, calibrator, thresholds or index; the affected artefact must be rebuilt and the experiment log updated.

---

## 2. Load order

```text
defaults in config.yaml
   ↓ overridden by
file named in CLAIMSENSE_CONFIG (optional, e.g. configs/pr11/modernbert-r16-lr2e4.yaml)
   ↓ overridden by
command-line flags of the specific command (e.g. --max-docs, --seed)
```

- An override file contains **only the keys it changes**; it is deep-merged into `config.yaml`.
- Environment variables never override config keys. They supply secrets and machine paths only (§5), so a run's behaviour is always fully described by its resolved config.
- Every command logs the **resolved** config (all keys, after merging) as an MLflow artefact or at the top of its log file (`../modelling/experiment-log.md` §3).

```bash
uv run python -m claimsense.config show                  # print the resolved config
uv run python -m claimsense.config show --section retrieve
uv run python -m claimsense.config check                 # validate only; exit 1 on error
```

---

## 3. `config.yaml` reference

**Tags:** **V** = part of the dataset `config_hash` (new version on change) · **M** = rebuild a model artefact on change · **—** = runtime only.

### 3.1 `project` and `paths`

```yaml
project:
  name: claimsense
  version: "1.0.0"                 # also used in the collectors' User-Agent
  seed: 13                         # default seed for anything not seeded elsewhere
  seeds: [13, 42, 2027]            # fine-tuning seeds (finetuning-spec.md §7)

paths:
  data_dir: data                   # overridable by CLAIMSENSE_DATA_DIR (Kaggle/Colab)
  models_dir: models
  index_dir: index/precedents
  reports_dir: reports
  cache_dir: data/cache            # LLM response cache (prompt-spec.md §6)
```

| Key | Meaning | Tag |
|---|---|---|
| `project.seed` | Seed for bootstrap, sampling and any unseeded step | — (bootstrap seed is fixed separately in `eval`) |
| `project.seeds` | The three fine-tuning seeds; the shipped model is the median one | M |
| `paths.*` | Relative to the repo root unless an env var overrides | — |

### 3.2 `collect` (PRs 3–4)

Full description and per-source notes: `../data/collection-runbook.md` §2.

```yaml
collect:
  contact_email: ""                # REQUIRED before any live run; collectors refuse to start if empty
  user_agent: "ClaimSense/{version} (non-commercial research; contact: {contact_email})"
  min_interval_s: 3.0              # NFR-08: validation rejects < 2.0
  jitter_s: 0.5
  timeout_s: 30
  max_retries: 3
  backoff_base_s: 10
  stop_after_consecutive_failures: 10
  sources:
    cioins: {enabled: false, start: "https://cioins.co.in/AwardsHArchive",
             products: [individual_mediclaim, group_mediclaim, overseas_mediclaim]}
    fos:    {enabled: false, product_filter: "Insurance",
             health_keywords: [medical, health, hospital, surgery, treatment, "private medical", "critical illness"]}
    fspo:   {enabled: true,  product_filter: "Health, Accident and Other"}
```

| Key | Tag | Note |
|---|---|---|
| `contact_email` | — | Your own address; it appears in the User-Agent. Kept in `config.yaml` because publishers must be able to see it, but **leave it empty in commits** and set it through a local override file if you prefer (`configs/local.yaml`, git-ignored) |
| `min_interval_s`, `jitter_s`, retries | — | Politeness only; do not change what is collected |
| `sources.*.enabled` | **V** | Flip only after `../data/terms-of-use-audit.md` clears the source |
| `fos.health_keywords`, `*.products`, `*.product_filter` | **V** | Decide which documents count as health |

### 3.3 `parse`, `segment`, `label`, `anonymise` (PRs 5–6)

```yaml
parse:
  ocr_min_chars: 200               # text layer below this → Tesseract
  ocr_lang: eng
  ocr_dpi: 300

segment:
  rules_version: {cioins: per-office, fos: fos/v1, fspo: fspo/v1}

label:
  rules_version: v1
  exclude_outcomes: [non_entertainable, withdrawn, settled]

anonymise:
  rules_version: v1
  presidio_score_threshold: 0.5
  extra_patterns: [in_phone, in_pin, in_aadhaar_like, in_pan_like, policy_number, claim_number]
```

All keys here are **V**. Each `rules_version` string is written into `build_meta.json` so a rule change is visible in the version's identity.

### 3.4 `dataset` (PR 7)

```yaml
dataset:
  dedup: {method: minhash, num_perm: 128, shingle: 5, threshold: 0.8}   # threshold set by audit A4
  split: {train_end: "2023-12-31", val_end: "2024-12-31"}
  sparse_split_min: 30            # flag a source with < 30 records in val or test
```

All **V**. Changing `split` also forces **every** model to be retrained and re-evaluated (`dataset-versioning.md` §4).

### 3.5 `baselines` and `finetune` (PRs 9–11)

```yaml
baselines:
  tfidf: {ngram_range: [1, 2], min_df: 3, C_grid: [0.1, 1, 10]}
  embed_encoder: BAAI/bge-small-en-v1.5      # same encoder as retrieval (B4)

finetune:
  base_model: answerdotai/ModernBERT-base
  base_model_revision: ""                    # Hub commit hash; filled in PR 11
  max_length: 1024
  truncation: head_tail_0.75
  lora: {r: 16, lora_alpha: 32, lora_dropout: 0.1, bias: none}
  train:
    learning_rate: 2.0e-4
    num_epochs: 4
    per_device_batch_size: 4
    gradient_accumulation_steps: 4
    precision: fp16
    class_weights: inverse_sqrt_frequency
    eval_every_steps: 200
    save_every_steps: 200
    max_run_minutes: 90
```

All **M**. The 12-configuration search (`finetuning-spec.md` §5) is a set of override files under `configs/pr11/`, one per configuration, so each run's settings are a committed file.

### 3.6 `calibrate` (PR 12)

```yaml
calibrate:
  method: temperature              # or isotonic; chosen by the rule in calibration.md §4
  crossfit_folds: 5
  ece_bins: 15
  isotonic_min_val: 1000           # isotonic only if val has at least this many records
  isotonic_min_gain: 0.01
```

All **M** (the calibrator and the abstain threshold are refitted on change).

### 3.7 `input`, `topic`, `retrieve`, `abstain` (PRs 13, 16)

```yaml
input:
  min_chars: 80
  max_chars: 6000

topic:
  method: keyword_and_classifier
  health_terms: [hospital, admitted, admission, surgery, treatment, diagnosis, doctor, discharge,
                 mediclaim, cashless, "day care", OPD]
  claim_terms: [claim, policy, insurer, insurance, TPA, repudiat*, reject*, denied, declined,
                reimburse*, settle*]
  in_scope_pass_rate: 0.99         # threshold chosen so ≥ 99% of val in-scope facts pass

retrieve:
  encoder: BAAI/bge-small-en-v1.5
  encoder_revision: ""             # filled in PR 13
  window_tokens: 400
  overlap_tokens: 50
  k: 5
  max_k: 20
  min_k: 2
  min_similarity: 0.35             # replaced by the val 5th percentile in PR 13

abstain:
  threshold: 0.55                  # replaced in PR 16 by the rule in abstention-policy.md §3
  threshold_floor: 0.50
  target_selective_accuracy: 0.75
  target_coverage: 0.50
```

| Key | Tag | Tuned in | Mirror artefact |
|---|---|---|---|
| `input.*` | — | Fixed | — |
| `topic.*_terms` | M (topic classifier) | PR 16 | `models/topic_clf.pkl` |
| `retrieve.encoder`, window, overlap | M (index rebuild) | PR 13 | `index/precedents/index_meta.json` |
| `retrieve.k` | — | PR 13 (k sweep) | — |
| `retrieve.min_k`, `min_similarity` | — | PR 13 | `models/thresholds.json` |
| `abstain.threshold` | — | PR 16 | `models/thresholds.json` |
| `abstain.target_*`, `threshold_floor` | — | **Fixed before PR 16 runs**; may change once, with a reason | — |

`claimsense.pipeline.load()` compares every mirrored value with `models/thresholds.json` and raises `ArtifactMismatchError` if they differ.

### 3.8 `llm`, `explain`, `cite_check` (PRs 10, 13)

```yaml
llm:
  provider: groq                   # groq | gemini
  model: ""                        # exact model ID, pinned in PR 10 (prompt-spec.md §3)
  model_checked_on: ""             # date the ID was confirmed on the provider
  temperature: 0
  top_p: 1
  seed: 13                         # sent only if the provider supports it
  response_format: json
  timeout_s: 20
  retries: 2
  max_output_tokens: {P-ZS: 200, P-EX: 400}
  cache: true                      # offline runs only; live app calls are never cached

explain:
  prompt_id: P-EX-v1
  max_sentences: 5
  excerpt_windows: 2
  excerpt_window_chars: 600

cite_check:
  model: cross-encoder/nli-deberta-v3-base
  model_revision: ""               # filled in PR 13
  min_entailment: 0.7              # tuned on the val dev set (E-017)
```

| Key | Tag | Note |
|---|---|---|
| `llm.provider`, `llm.model` | M (B5 and explanation metrics) | A model change is a **new prompt version** (`prompt-spec.md` §1, §3) |
| `llm.temperature`, `top_p`, `seed` | M | Fixed at 0 / 1 / 13 for repeatability |
| `explain.max_sentences` | — | First lever if latency (E8) fails |
| `cite_check.min_entailment` | M (explanation metrics) | Changing it after A6 needs a fresh A6 sample |

> **Reconciliation note.** `pipeline-interface.md` §6 lists `explain.provider` and `explain.retries`. They live under `llm` here (`llm.provider`, `llm.retries`) so the zero-shot baseline and the explainer share one provider block, as `prompt-spec.md` §3 already does. `pipeline-interface.md` §6 should point here.

### 3.9 `eval`, `tracking`, `app`

```yaml
eval:
  bootstrap_resamples: 1000
  bootstrap_seed: 13
  stratify_by: source
  min_slice_n: 30
  min_ece_n: 100
  audit_seeds: {A5A6: 2025, errors: 2026}

tracking:
  backend: mlflow                  # mlflow | mlflow+wandb (metrics-only mirror)
  experiment_prefix: pr
  wandb_project: claimsense

app:
  title: ClaimSense
  default_country: IN              # preselected in the country box; user can change it
  probability_rounding: 0.1        # "about 7 in 10"
  show_exact_on_hover: true
```

`eval.*` keys are **frozen with the evaluation protocol** (`../evaluation-protocol.md` §2): changing one after the `eval-protocol-v1` tag is a logged deviation.

---

## 4. Artefact files that mirror config

| File | Written by | Holds | Checked against |
|---|---|---|---|
| `data/processed/<v>/build_meta.json` | `make build` | `config_hash` of the **V** keys, rule versions, split dates | Resolved config at build time |
| `models/lora-adapter/meta.json` | PR 11 | Base model + revision, max length, LoRA settings, `dataset_version`, `run_id` | `finetune.*`, `data/processed/LATEST` |
| `models/calibrator.pkl` | PR 12 | Method, temperature, `model_run_id`, `dataset_version` | Adapter `meta.json` |
| `models/thresholds.json` | PR 13, PR 16 | `abstain_threshold`, `topic_threshold`, `retrieve_min_similarity`, `retrieve_min_k` | `abstain.threshold`, `retrieve.*` |
| `index/precedents/index_meta.json` | `make index` | Encoder + revision, chunking, `dataset_version` | `retrieve.*`, `data/processed/LATEST` |

---

## 5. Environment variables

Loaded from `.env` by `python-dotenv` at start-up (local only). In CI they are set in the workflow; on Kaggle and Colab through their Secrets panels.

### 5.1 Secrets

| Variable | Needed for | Required when | Where to get it |
|---|---|---|---|
| `GROQ_API_KEY` | Zero-shot baseline B5, explanations | `llm.provider: groq` and an LLM call is actually made | Groq console → API Keys |
| `GEMINI_API_KEY` | Same | `llm.provider: gemini` | Google AI Studio → Get API key |
| `WANDB_API_KEY` | Metrics mirror | `tracking.backend: mlflow+wandb` | wandb.ai → User settings |
| `KAGGLE_USERNAME`, `KAGGLE_KEY` | Uploading the private dataset; downloading notebook output | PR 11 | Kaggle → Settings → API (or `~/.kaggle/kaggle.json`) |

Rules:

- Only the key for the **selected** provider is needed. A missing key fails only when an LLM call is attempted, with `ExplainerUnavailableError` and a message naming the variable; everything else still runs, and the app shows the prediction without an explanation (`pipeline-interface.md` §5).
- **CI has no LLM keys.** The explainer is a stub there (`../testing/test-strategy.md` §8); a test that needs a real key is a bug.
- Before using a key, record the provider's free-tier limits and data-retention terms in the PR 10 description, and pick the setting that does not train on API inputs where one exists (`privacy-impact-assessment.md` P-R7).
- Rotate a key immediately if it is ever printed in a log, a notebook output or a commit.

### 5.2 Behaviour and paths

| Variable | Default | Effect |
|---|---|---|
| `CLAIMSENSE_CONFIG` | unset | Path of an override file merged on top of `config.yaml` (§2) |
| `CLAIMSENSE_ENV` | `local` | `ci` turns on the network block and stubs; `kaggle` / `colab` set notebook-friendly logging |
| `CLAIMSENSE_DATA_DIR` | `data` | Where `data/processed/` is read from (Kaggle input, Drive) |
| `CLAIMSENSE_OUT_DIR` | repo root | Where checkpoints, `models/` and `mlruns/` are written on Kaggle/Colab |
| `MLFLOW_TRACKING_URI` | `file:./mlruns` | MLflow store |
| `HF_HUB_OFFLINE` | unset locally, `1` in CI | Blocks model downloads; forces stubs in CI |
| `HF_HOME` | Hugging Face default | Model cache location |
| `CUDA_VISIBLE_DEVICES` | unset | Set to `""` to prove CPU-only inference (NFR-07b) |
| `TOKENIZERS_PARALLELISM` | `false` | Silences fork warnings in Streamlit and pytest |

### 5.3 `.env.example` (committed)

```dotenv
# Copy to .env and fill in only what you need. Never commit .env.
# LLM provider: set the key matching llm.provider in config.yaml
GROQ_API_KEY=
GEMINI_API_KEY=

# Optional
WANDB_API_KEY=
KAGGLE_USERNAME=
KAGGLE_KEY=

# Optional behaviour
# CLAIMSENSE_CONFIG=configs/local.yaml
# HF_HUB_OFFLINE=1
```

---

## 6. Streamlit settings (`.streamlit/config.toml`)

```toml
[browser]
gatherUsageStats = false     # privacy-impact-assessment.md P-R8

[server]
headless = true
address = "localhost"        # v1 is local only (responsible-use.md §4)
maxUploadSize = 1            # no file uploads in v1

[runner]
magicEnabled = false
```

---

## 7. Tests

| Test | Checks |
|---|---|
| `test_config.py::test_loads_and_validates` | `config.yaml` parses into the schema with no unknown keys |
| `test_config.py::test_min_interval_floor` | `collect.min_interval_s < 2.0` is rejected (NFR-08) |
| `test_config.py::test_no_secrets` | No key name contains `key`, `token` or `secret` with a non-empty value |
| `test_config.py::test_override_merge` | An override file changes only its own keys |
| `test_config.py::test_config_hash_covers_v_keys` | Changing any **V** key changes `config_hash`; changing a runtime key does not |
| `test_thresholds_mismatch` | `config.yaml` and `models/thresholds.json` disagreeing raises `ArtifactMismatchError` |
