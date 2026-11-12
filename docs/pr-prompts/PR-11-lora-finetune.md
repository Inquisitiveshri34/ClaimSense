# PR 11 · LoRA fine-tune

| | |
|---|---|
| **Branch** | `feat/lora-finetune` |
| **Depends on** | PR 10 |
| **Covers** | FR-11, NFR-07 · **Risks** R8, R9 |
| **Read first** | `docs/modelling/finetuning-spec.md` (all), `docs/modelling/experiment-log.md`, `docs/operations/setup.md` §5–§6, `docs/operations/configuration.md` §3.5, §4 |
| **Done when** | The fine-tuned model beats every baseline on validation (real run on Kaggle/Colab), and the training/inference code is proven offline by a tiny CPU smoke run |

---

## 1. Goal

LoRA fine-tuning of `answerdotai/ModernBERT-base` for 3-class classification on a free GPU, plus a CPU inference wrapper that later PRs load. Because CI has no GPU and no internet, the same code path must also run in a **smoke mode**: a tiny randomly initialised model and an offline tokenizer, on CPU, in seconds.

## 2. Files to add

| File | Contents |
|---|---|
| `src/claimsense/models/finetune.py` | `train(config: str | Path, seed: int, resume: bool = True, smoke: bool = False) -> RunResult`. Pre-flight (non-smoke): data content hash == `build_meta.json` `dataset_version` else `DataVersionMismatch`; `torch.cuda.is_available()`; after 50 steps project runtime and abort if > `max_run_minutes`. Model: `AutoModelForSequenceClassification` + PEFT LoRA (`r`, `alpha`, `dropout`, target modules per spec), head-tail truncation (`head_tail_0.75`), class weights `inverse_sqrt_frequency`, fp16 on GPU, checkpoints every `save_every_steps` to `CLAIMSENSE_OUT_DIR`, resume from last checkpoint, early stop on val macro-F1. Saves `models_dir()/lora-adapter/{adapter_model.safetensors, head.safetensors, meta.json}` (base model + revision, max_length, LoRA settings, `dataset_version`, `run_id`, seed, `trained_on`). **Smoke mode:** `ModernBertConfig` with tiny dims (e.g. hidden 32, 2 layers, 2 heads) built in code, random init, tokenizer built offline with `tokenizers` WordLevel/BPE from the training texts, CPU, ≤ 20 steps |
| `src/claimsense/models/classifier.py` | `LoraClassifier.load(dir)` implements `Classifier`: loads base (or smoke config) + adapter, CPU, batch inference, returns logits and probabilities in `LABELS` order; `model_version = run_id` |
| `src/claimsense/models/search.py` | Runs the 12-configuration search over `configs/pr11/*.yaml` × `project.seeds`; picks the best config by val macro-F1; ships the **median-seed** run |
| `configs/pr11/*.yaml` | 12 override files per `finetuning-spec.md` §5 |
| `notebooks/kaggle_finetune.ipynb` | Thin wrapper exactly as `setup.md` §5.3 |
| `requirements-train-kaggle.txt` | `uv export` without torch (script `scripts/export_kaggle_reqs.sh`) |
| `tests/unit/test_adapter_meta.py`, `tests/unit/test_finetune_preflight.py`, `tests/unit/test_truncation.py`, `tests/integration/test_finetune_smoke.py` | See §4 |

## 3. Files to modify

`config.yaml` (`finetune`, pin `base_model_revision`; **M**), `config.py`, `pyproject.toml` (`train` extra: `transformers`, `peft`, `accelerate`, `safetensors`, `tokenizers`, `kaggle`; `transformers`/`peft`/`safetensors`/`tokenizers` also in main deps for CPU inference), `scripts/ci_guard.sh` (rule `no-base-weights`: no `*.safetensors|*.bin|*.pt` > 50 MB; under `models/` only `adapter_model.safetensors` / `head.safetensors`), `src/claimsense/tracking.py` (`python -m claimsense.tracking import-runs <dir>`), `Makefile` (`finetune-smoke`, `bench-classifier`), `docs/operations/setup.md` (current Kaggle quota note), `docs/modelling/experiment-log.md` (table markers for generated results), `CHANGELOG.md`.

## 4. Tests to write

- **`test_truncation.py`**: head-tail keeps the first 75% and last 25% of the token budget; short texts untouched.
- **`test_finetune_preflight.py`**: wrong data hash → `DataVersionMismatch` before any model is built; no CUDA in non-smoke → clear error; projected runtime over cap → abort (simulate step timings).
- **`test_adapter_meta.py`**: `meta.json` schema; `dataset_version` present; guard rejects a fake 60 MB `models/x.bin` in a temp repo.
- **`test_finetune_smoke.py`**: `train(..., smoke=True)` on the mini dataset finishes on CPU in < 60 s, saves adapter + meta; `LoraClassifier.load` returns `(n,3)` probabilities summing to 1; resume from the saved checkpoint continues the step counter; same seed → same val predictions.

## 5. E2E tests

`stages.py`: `run_finetune(world)` → `run_build`, then `train(smoke=True)` on the world dataset.

**`tests/e2e/test_e2e_11_finetune.py`**:
- Smoke fine-tune on the world dataset produces `models_dir()/lora-adapter/` with `meta.json.dataset_version == LATEST`.
- `LoraClassifier` loads with `CUDA_VISIBLE_DEVICES=""` and predicts on world val; run appears in MLflow with the same metric keys as the baselines (so the PR 14 report can compare them).
- (No "beats baselines" assertion here: the smoke model is random-sized; that gate is the real Kaggle run.)
- Contracts extended: adapter `meta.json` version.

## 6. Definition of done

`make pr-check` → ALL CHECKS PASSED (CPU only); raise the floor.

## 7. Manual checks (Diya)

- [ ] Kaggle setup per `docs/operations/setup.md` §5 (private dataset!). Attaching the wrong dataset version → notebook refuses to start.
- [ ] Run the search; download outputs; `uv run python -m claimsense.tracking import-runs ./kaggle_out/mlruns`; copy the median-seed adapter to `models/lora-adapter/`.
- [ ] Paste the val table (best config, 3 seeds, median) next to B1–B5. **Gate: beats every baseline.**
- [ ] `CUDA_VISIBLE_DEVICES="" make bench-classifier` → paste time per query.
- [ ] `git ls-files models/` shows no base-model weights.
