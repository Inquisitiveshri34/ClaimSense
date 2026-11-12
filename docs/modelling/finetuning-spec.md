# ClaimSense — Fine-tuning Specification

> How the ClaimSense classifier is fine-tuned: which base model and why, how long inputs are handled, the LoRA configuration, the training recipe, the GPU budget on free hardware, and the seed policy that makes the reported numbers honest.

**Author:** Diya Shrivastava · **Owning PR:** 11 · **Status:** Planned

**Related:** FR-11, design decision D4, NFR-05 (reproducibility), NFR-06 (latency), NFR-07 (cost), risks R7, R8, R9, `baselines.md`, `experiment-log.md`, `calibration.md`, `../data/dataset-versioning.md`.

---

## 1. Goal and done-when

- **Goal:** a 3-class classifier over `facts_text` that beats every baseline in `baselines.md` on validation, runs on a laptop CPU at inference, and ships as a small LoRA adapter.
- **Done when (PR 11):** mean val macro-F1 over 3 seeds is higher than each of B1–B5, adapter weights are saved to `models/lora-adapter/`, and every run is logged.

---

## 2. Base model choice

### Criteria

| Criterion | Why it matters | Hard limit |
|---|---|---|
| Context length | `facts_text` can reach ~6,000 characters (≈ 1,500 tokens) | Should cover most records without truncation |
| CPU inference speed | NFR-06: whole `predict()` ≤ 10 s on a laptop CPU | Classifier share ≤ 3 s |
| Fits a free GPU | NFR-07: Kaggle/Colab T4 or P100, 16 GB | Training fits with LoRA |
| Licence | Weights downloaded by users; adapter published | Permissive (Apache-2.0 / MIT) |
| Library support | `transformers` + `peft` sequence classification | Supported out of the box |

### Candidates

| Rank | Model | Type | Params | Context | Licence | Role |
|---|---|---|---|---|---|---|
| **1** | `answerdotai/ModernBERT-base` | Encoder | ~150 M | 8,192 tokens | Apache-2.0 | **Primary** |
| 2 | `microsoft/deberta-v3-base` | Encoder | ~185 M | 512 tokens (trained length) | MIT | Fallback if ModernBERT is unstable |
| 3 | `Qwen/Qwen2.5-1.5B` | Decoder + classification head | ~1.5 B | 32 K | Apache-2.0 | Stretch, only if encoders plateau **and** the CPU latency check passes |

Figures are from the public model cards; confirm the licence and size on each card when PR 11 opens and paste the links into the PR description.

### Why an encoder first

- Classification is the whole task; an encoder with a classification head is the standard tool and trains in minutes, not hours.
- ModernBERT's long context removes most truncation, which matters because the insurer's reason often sits at the **end** of the facts.
- A 150 M model runs on CPU well inside the latency budget; a 1.5 B decoder over 1,500 tokens may not.

### Selection procedure

1. Pilot each of the top two candidates: 1 seed, 2 epochs, default LoRA config (§4).
2. Measure CPU latency of the merged model on 20 val inputs at the chosen max length.
3. Keep the candidate with the higher val macro-F1 among those with median CPU latency ≤ 3 s.
4. Try the stretch model only if the winner is within 1 macro-F1 point of the best baseline.
5. Record the choice as an ADR and in the experiment log.

`ModernBERT` needs a recent `transformers` release; pin the exact version in `pyproject.toml` at PR 11.

---

## 3. Input formatting

| Setting | Value |
|---|---|
| Text | `facts_text` exactly as stored (anonymiser tokens kept) |
| Max length | 1,024 tokens (ModernBERT); 512 for DeBERTa fallback |
| Truncation | **Head + tail**: first 75% and last 25% of the token budget, joined by `[SEP]` |
| Metadata prefix | None in v1. A country prefix (`[IN]`, `[GB]`, `[IE]`) is tried as one ablation run, because live users would need to state their country |
| Reported | Share of train/val records truncated at the chosen max length |

Head + tail keeps both the opening (what happened) and the closing (why the insurer refused), which is where the signal usually is.

---

## 4. LoRA configuration

```yaml
lora:
  task_type: SEQ_CLS
  r: 16
  lora_alpha: 32
  lora_dropout: 0.1
  bias: none
  target_modules:            # confirm by printing model.named_modules() in PR 11
    modernbert: [Wqkv, Wo, Wi]
    deberta_v3: [query_proj, key_proj, value_proj, dense]
    qwen2_5: [q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj]
  modules_to_save: [classifier, head]   # the new classification head is trained in full
  num_labels: 3
  id2label: {0: rejected, 1: partially_upheld, 2: upheld}
```

- Only adapter and head weights are saved; the base model is downloaded by ID (`../architecture/data-schema.md` §6).
- The label order is fixed here and copied into `meta.json`; calibration and the pipeline read it from there, never assume it.

---

## 5. Training recipe

```yaml
train:
  learning_rate: 2.0e-4
  lr_scheduler: linear
  warmup_ratio: 0.06
  num_epochs: 4
  early_stopping: {metric: val_macro_f1, patience: 2}
  per_device_batch_size: 4
  gradient_accumulation_steps: 4      # effective batch 16
  weight_decay: 0.01
  max_grad_norm: 1.0
  precision: fp16                     # T4/P100 have no bf16
  gradient_checkpointing: false       # true for the Qwen stretch model
  loss: weighted_cross_entropy
  class_weights: inverse_sqrt_frequency   # computed from train counts (R7)
  eval_every_steps: 200
  save_every_steps: 200
  save_total_limit: 2
```

### Search space (kept small on purpose)

| Hyperparameter | Values |
|---|---|
| `r` | 8, 16 |
| `learning_rate` | 1e-4, 2e-4, 5e-4 |
| Class weights | none, inverse-sqrt |

12 configurations × 1 seed, ranked by val macro-F1. The **top 2** are then run with all 3 seeds (§7). No other hyperparameters are tuned, and the search space is fixed before PR 11's first run so it cannot grow to chase a result.

### Ablations (one seed each, reported, not used for selection)

- Country prefix on vs off (§3).
- Max length 512 vs 1,024.
- Lexicon terms masked vs not (L2, feeds PR 14).

---

## 6. GPU budget

### Hardware

| Host | GPU | Notes |
|---|---|---|
| Kaggle Notebooks (primary) | T4 ×2 or P100, 16 GB each | Weekly GPU-hour quota and per-session time limit; check the current figures when PR 11 opens |
| Google Colab free (backup) | T4, 16 GB | Availability varies; sessions can disconnect without warning |

### Budget for PR 11

| Block | GPU-hours |
|---|---|
| Pilot (2 candidates × 1 run) | 3 |
| Search (12 configs × 1 seed) | 12 |
| Final seeds (2 configs × 3 seeds) | 6 |
| Ablations (3 runs) | 2 |
| Reserve (reruns, crashes) | 4 |
| **Total cap** | **27** |

Rules:

1. **Per-run cap: 90 minutes.** After 50 optimiser steps, the script extrapolates total time and aborts if the projection exceeds the cap.
2. **Checkpoint every 200 steps** to the notebook's persistent output (Kaggle) or Drive (Colab); every run can resume from its last checkpoint (R9).
3. GPU-hours per run are logged as a metric; the running total is kept in the experiment-log index.
4. If the budget runs out, stop the search, keep the best configuration found, and say so in the PR description.

### Getting the data to the GPU

- Upload only `data/processed/<version>/` as a **private** Kaggle dataset (or pull it through a private DVC remote). Never a public dataset: the source terms may not allow redistribution (`../data/terms-of-use-audit.md`).
- The training script checks the loaded data's content hash against `dataset_version` and refuses to start on a mismatch.

---

## 7. Seeds and determinism

| Rule | Value |
|---|---|
| Seeds | `13`, `42`, `2027` |
| Set via | `transformers.set_seed(seed)` (Python, NumPy, PyTorch, CUDA) |
| Determinism | `torch.use_deterministic_algorithms(True, warn_only=True)`; remaining GPU non-determinism is accepted and visible in the seed spread |
| Reported | Mean ± standard deviation of val macro-F1 over 3 seeds |
| Shipped model | The seed with the **median** val macro-F1, not the best one, so the shipped model is typical rather than lucky |
| "Beats every baseline" | Uses the 3-seed **mean** |

---

## 8. Outputs

```text
models/lora-adapter/
├── adapter_config.json
├── adapter_model.safetensors
├── head.safetensors              # if not inside the adapter file
└── meta.json
models/logits/
└── val.npy                       # raw logits on val, read by calibration.md
```

`meta.json`:

```json
{
  "run_id": "<tracker run ID>",
  "base_model": "answerdotai/ModernBERT-base",
  "base_model_revision": "<commit hash on the Hub>",
  "dataset_version": "v________",
  "seed": 42,
  "max_length": 1024,
  "truncation": "head_tail_0.75",
  "id2label": {"0": "rejected", "1": "partially_upheld", "2": "upheld"},
  "lora": {"r": 16, "alpha": 32, "dropout": 0.1},
  "val_macro_f1": null,
  "trained_on": "kaggle-t4"
}
```

- `base_model_revision` pins the exact Hub commit, so a later update to the base model cannot silently change results.
- Test logits are **not** produced in PR 11. They are written only by the evaluation command (PR 12 gate, PR 14 report).

---

## 9. CPU inference check

Run in PR 11, repeated in PR 16 (`bench_latency.py`):

1. Merge the adapter into the base model (`merge_and_unload`), load on CPU with `CUDA_VISIBLE_DEVICES=""`.
2. Time 20 val inputs at max length after one warm-up call.
3. **Pass:** median ≤ 3 s, max ≤ 5 s on the reference laptop (record its CPU and RAM in the PR).

If it fails: reduce max length, try dynamic int8 quantisation of linear layers, or fall back to the smaller candidate.

---

## 10. If fine-tuning does not win (R8)

1. Check for bugs first: label order, truncation side, class weights, learning rate too high.
2. Compare per-class F1: a model that never predicts `partially_upheld` can lose on macro-F1 while winning on accuracy.
3. If it still loses, report the result honestly with the analysis, and ship the strongest model (possibly B3 or B4) as the production classifier. Calibration, retrieval and explanation work the same either way.

---

## 11. Code and tests

```text
src/claimsense/models/finetune.py   # train(), resume(), export_adapter()
notebooks/kaggle_finetune.ipynb     # thin wrapper: install, pull data, call finetune.train()
tests/test_finetune.py
```

| Test | Checks |
|---|---|
| `test_tiny_train_step` | One training step on a 16-row fixture with a tiny random model runs on CPU |
| `test_label_order` | `meta.json` `id2label` matches `schema.Label` order used by calibration |
| `test_head_tail_truncation` | Long input keeps the first 75% and last 25% of the token budget |
| `test_data_hash_check` | Training refuses a dataset whose hash differs from `dataset_version` |
| `test_adapter_roundtrip` | Saved adapter reloads and gives identical logits on the fixture |
