# ClaimSense — Setup

> How to get a working ClaimSense development environment: the system tools, the Python version and lock file, the first commands to run, and how to set up the Kaggle and Colab notebooks used for GPU fine-tuning. Following this file on a clean machine should end with `make test` green.

**Author:** Diya Shrivastava · **Owning PR:** 1 (local environment); Kaggle/Colab section completed in PR 11 · **Status:** Planned

**Related:** NFR-05 (pinned dependencies), NFR-07 (free compute), NFR-10 (lint and tests), `configuration.md`, `ci-cd.md`, `reproduction.md`, `../testing/test-strategy.md` §4, `../modelling/finetuning-spec.md` §6, `../data/collection-runbook.md` §1, `../responsible-ai/privacy-impact-assessment.md` (P-R5, P-R6).

---

## 1. What runs where

| Work | Where | GPU? | Data present? |
|---|---|---|---|
| Collection, parsing, labelling, dataset build (PRs 3–7) | Laptop | No | Yes (`data/`, git-ignored) |
| Baselines, embeddings, calibration, retrieval, evaluation (PRs 8–10, 12–15) | Laptop | No (CPU is enough) | Yes |
| Zero-shot baseline B5, explanations (PRs 10, 13) | Laptop → LLM API (Groq or Gemini) | No | Anonymised text only is sent |
| LoRA fine-tuning (PR 11) | **Kaggle Notebook** (primary) or **Colab** (backup) | Yes (T4 / P100) | `data/processed/<version>/` only, as a **private** dataset |
| Inference, Streamlit app (PRs 16–17) | Laptop | No | Models + index only |
| CI | GitHub Actions | No | **No data, no network** (fixtures only) |

The rule from `privacy-impact-assessment.md`: **raw and interim data never leave the laptop.** Only the processed, anonymised version goes to Kaggle or Colab, and only privately.

---

## 2. Prerequisites

### 2.1 System tools

| Tool | Version | Why | Check |
|---|---|---|---|
| Python | **3.11.x** (same as CI) | Every pinned dependency is resolved against 3.11 | `python3.11 --version` |
| uv | ≥ 0.4 | Installs from the lock file; creates `.venv/` | `uv --version` |
| Git | ≥ 2.40 | — | `git --version` |
| GNU Make | any | Every routine command is a `make` target | `make --version` |
| Tesseract OCR | ≥ 5.0, English data | OCR fallback for scanned awards (PR 5) | `tesseract --version` |
| Disk | ≥ 10 GB free | Raw PDFs (~5 GB, `collection-runbook.md` §1) + models + index | — |
| RAM | ≥ 8 GB (16 GB comfortable) | CPU inference of the merged classifier + NLI model | — |

The tool choice (**uv** with a committed `uv.lock`) is fixed in PR 1. If uv is not available, §3.3 gives a plain-`pip` path from the exported lock file; both install identical versions.

### 2.2 Installing the system tools

| OS | Commands |
|---|---|
| **Ubuntu / WSL2** | `sudo apt-get install -y python3.11 python3.11-venv make tesseract-ocr tesseract-ocr-eng` then `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **macOS** | `brew install python@3.11 make tesseract uv` |
| **Windows** | Use **WSL2 with Ubuntu** and follow the Ubuntu row. Native Windows is not supported: `make`, Tesseract paths and file-locking during collection behave differently, and CI runs on Ubuntu |

### 2.3 Accounts (only when the PR needs them)

| Account | Needed from | Used for | Cost |
|---|---|---|---|
| GitHub | PR 1 | Repo, Actions, branch protection | Free |
| Kaggle (phone-verified, for GPU access) | PR 11 | Fine-tuning notebook, private dataset | Free |
| Google (Colab, Drive) | PR 11, backup only | Backup GPU, checkpoint storage | Free |
| Groq **or** Google AI Studio (Gemini) | PR 10 | Zero-shot baseline B5, explanations | Free tier |
| Weights & Biases | Optional | Metrics-only mirror of MLflow runs | Free personal tier |
| Hugging Face | Not required | Public models download without an account | — |

API keys go in `.env`, never in `config.yaml` or a notebook cell (`configuration.md` §5).

---

## 3. Local setup

### 3.1 First-time steps

```bash
# 1. clone
git clone https://github.com/Inquisitiveshri34/claimsense.git
cd claimsense

# 2. create .venv and install exactly what uv.lock pins (dev + test extras)
uv sync --frozen --all-extras

# 3. git hooks: ruff, black, the data/PDF guard (P-R5)
uv run pre-commit install

# 4. secrets and local settings
cp .env.example .env            # then fill in only the keys you need (configuration.md §5)

# 5. set your contact email for the collectors' User-Agent (NFR-08)
#    config.yaml → collect.contact_email

# 6. prove it works
make lint
make test
```

`make test` must pass on a fresh clone with **no data and no API keys**. That is the same run CI does (`ci-cd.md` §3).

### 3.2 Everyday commands

All commands run inside the virtual environment; the Makefile calls `uv run` for you.

| Command | What it does |
|---|---|
| `make lint` | `ruff check .` and `black --check .` |
| `make fmt` | `ruff check --fix .` and `black .` |
| `make test` | Fast suite: unit, collector, integration, pipeline, app, leak (fixture mode) |
| `make test-leak` | Leak probes only |
| `make test-data` | Data-quality tests on the real processed dataset (`local_data`) |
| `make test-slow` | Tests that load real heavy models (NLI cross-encoder) |
| `make bench` | CPU latency benchmark (NFR-06) |
| `make build` | Parse → segment → label → anonymise → dedup → split → write `data/processed/v<hash>/` |
| `make index` | Build the precedent index for `data/processed/LATEST` |
| `make report` | Evaluation report (`reproduction.md`) |
| `make app` | Start the Streamlit app (`user-guide.md`) |
| `make reproduce` | Fresh-clone reproduction script (`reproduction.md`) |

Full test-command semantics: `../testing/test-strategy.md` §4. Collection commands: `../data/collection-runbook.md` §3.

### 3.3 Without uv (plain pip)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-lock.txt      # exported from uv.lock in CI; never edited by hand
pip install -e . --no-deps
pre-commit install
```

`requirements-lock.txt` is regenerated by `uv export --frozen --all-extras --no-hashes > requirements-lock.txt` whenever `uv.lock` changes, and a CI check fails if the two disagree.

### 3.4 CPU-only PyTorch

The laptop and CI never need CUDA. The lock file pins the **CPU wheel** of `torch` for Linux and macOS through a uv index override in `pyproject.toml`, which keeps the install around 200 MB instead of several GB. Kaggle and Colab already ship a CUDA build of `torch`; the notebook does not reinstall it (§5.3).

### 3.5 Pre-downloading models (optional, for offline work)

```bash
make models-cache
```

Downloads the pinned revisions of the base classifier (`answerdotai/ModernBERT-base`), the retrieval encoder (`BAAI/bge-small-en-v1.5`) and the NLI model (`cross-encoder/nli-deberta-v3-base`) into the Hugging Face cache. Revisions come from `models/lora-adapter/meta.json` and `index/precedents/index_meta.json` once those exist. After this, `HF_HUB_OFFLINE=1` works locally.

### 3.6 Directory layout after setup

```text
claimsense/
├── .env                  # yours only; git-ignored; blocked by the guard job
├── .venv/                # git-ignored
├── config.yaml           # committed; see configuration.md
├── uv.lock               # committed
├── requirements-lock.txt # committed; exported from uv.lock
├── src/claimsense/
├── tests/
├── notebooks/
│   ├── eda.ipynb                # PR 8
│   └── kaggle_finetune.ipynb    # PR 11, thin wrapper (§5)
├── data/                 # git-ignored; created by the collectors and `make build`
├── models/               # adapter + calibrator + thresholds; base weights never stored
├── index/precedents/     # FAISS index; git-ignored until the release decision in PR 18
├── mlruns/               # MLflow local store; git-ignored
└── reports/              # generated by `make report`
```

---

## 4. Local machine hygiene (privacy controls P-R5)

Do these once, before the first collection run:

| Control | How |
|---|---|
| Full-disk encryption | BitLocker (Windows host of WSL2) or FileVault (macOS) switched on |
| Project folder not cloud-synced | Exclude the repo from OneDrive, iCloud Drive, Google Drive and Dropbox |
| Pre-commit guard active | `pre-commit install` done (§3.1); it blocks `*.pdf` and any path under `data/raw/` |
| `.env` never committed | Already git-ignored; the CI `guard` job fails if one is tracked |

---

## 5. Kaggle notebook (primary GPU, PR 11)

### 5.1 One-time setup

1. **Verify your phone number** on Kaggle (Settings → Phone verification); GPU and internet access depend on it.
2. **Upload the processed dataset as a private Kaggle dataset.**
   ```bash
   # from the repo root, on the laptop
   uv run kaggle datasets init -p data/processed/<version>/      # creates dataset-metadata.json
   # edit dataset-metadata.json: title "claimsense-processed-<version>", "isPrivate": true
   uv run kaggle datasets create -p data/processed/<version>/ --dir-mode zip
   ```
   Check the dataset page says **Private** before attaching it to anything (P-R6). Upload only the files in the version directory: `train.parquet`, `val.parquet`, `test.parquet`, `schema.json`, `build_meta.json`. The data card can stay local.
3. **Kaggle API token** on the laptop: Kaggle → Settings → API → *Create New Token*, save to `~/.kaggle/kaggle.json`, then `chmod 600 ~/.kaggle/kaggle.json`.
4. **No API keys go into Kaggle.** Fine-tuning needs no LLM. If W&B mirroring is wanted, add `WANDB_API_KEY` through **Add-ons → Secrets**, never as a notebook cell.

### 5.2 Notebook settings

| Setting | Value |
|---|---|
| Accelerator | GPU T4 ×2 (or P100) |
| Internet | On (to install the pinned package and download the base model) |
| Persistence | Files only (keeps `/kaggle/working/` checkpoints between sessions where available) |
| Input | The private `claimsense-processed-<version>` dataset |
| Environment | "Pin to original environment" after the first successful run, so a Kaggle image update cannot change library versions mid-search |

Check the current weekly GPU quota and session limit when PR 11 opens and record them in the PR description (`finetuning-spec.md` §6).

### 5.3 Notebook cells (`notebooks/kaggle_finetune.ipynb`)

The notebook is a thin wrapper; all logic is in `src/claimsense/models/finetune.py`.

```python
# 1. install ClaimSense at an exact commit, keeping Kaggle's CUDA torch
COMMIT = "<git sha of the PR 11 branch>"
!pip install -q "claimsense[train] @ git+https://github.com/Inquisitiveshri34/claimsense.git@{COMMIT}" \
     --extra-index-url https://download.pytorch.org/whl/cu121 --no-deps
!pip install -q -r https://raw.githubusercontent.com/Inquisitiveshri34/claimsense/{COMMIT}/requirements-train-kaggle.txt

# 2. point at the private dataset and a persistent output dir
import os
os.environ["CLAIMSENSE_DATA_DIR"] = "/kaggle/input/claimsense-processed-<version>"
os.environ["CLAIMSENSE_OUT_DIR"]  = "/kaggle/working"
os.environ["MLFLOW_TRACKING_URI"] = "file:///kaggle/working/mlruns"

# 3. run one configuration (the search loops over configs in finetune.py)
from claimsense.models import finetune
finetune.train(config="configs/pr11/modernbert-r16-lr2e4.yaml", seed=42, resume=True)
```

`requirements-train-kaggle.txt` is exported from `uv.lock` **without** `torch`, so Kaggle's preinstalled CUDA build is kept and every other library matches the laptop.

What `finetune.train()` checks before using the GPU:

1. The loaded data's content hash equals `dataset_version` in `build_meta.json`; it refuses to start otherwise (`finetuning-spec.md` §6).
2. `torch.cuda.is_available()` is true.
3. After 50 optimiser steps it projects total run time and aborts if it exceeds the 90-minute per-run cap.

### 5.4 Getting results back

At the end of every session:

1. Download `/kaggle/working/mlruns/` and `/kaggle/working/models/lora-adapter/` (Output tab → download, or `kaggle kernels output <user>/<kernel> -p ./kaggle_out`).
2. Merge the runs into the repo's tracker:
   ```bash
   uv run python -m claimsense.tracking import-runs ./kaggle_out/mlruns
   ```
3. Copy the shipped adapter (the **median** seed, `finetuning-spec.md` §7) into `models/lora-adapter/`.
4. Run the CPU check on the laptop: `make bench-classifier` (`finetuning-spec.md` §9).

After v1.0 is tagged, **delete the private Kaggle dataset** (P-R6).

---

## 6. Google Colab (backup GPU)

Use Colab only when Kaggle quota is exhausted or unavailable.

| Step | Detail |
|---|---|
| Runtime | Runtime → Change runtime type → **T4 GPU** |
| Data | Upload `data/processed/<version>/` to a **private** Drive folder (`MyDrive/claimsense/data/<version>/`); never a shared link |
| Mount | `from google.colab import drive; drive.mount("/content/drive")` |
| Paths | `CLAIMSENSE_DATA_DIR=/content/drive/MyDrive/claimsense/data/<version>`; `CLAIMSENSE_OUT_DIR=/content/drive/MyDrive/claimsense/out` (checkpoints survive a disconnect) |
| Install | Same two `pip` lines as §5.3 |
| Resume | `finetune.train(..., resume=True)` picks up the last checkpoint after a disconnect (R9) |
| Secrets | Colab **Secrets** panel (key icon) for `WANDB_API_KEY` if used |

Record `trained_on: "colab-t4"` in `meta.json` for runs made here.

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `uv sync --frozen` fails: "lock file out of date" | `pyproject.toml` edited without re-locking | `uv lock`, commit both files |
| `make test` tries to reach the internet and fails | A test is missing its fixture; `pytest-socket` blocked it | That is the intended failure; add the fixture (`../testing/test-fixtures.md`) |
| `TesseractNotFoundError` | Tesseract not on `PATH` | Install per §2.2; check `which tesseract` |
| `local_data` tests all skipped | No `data/processed/` yet | Expected before PR 7; run `make build` once data exists |
| `ArtifactMismatchError` on `predict()` | Adapter, calibrator, thresholds or index built from a different `dataset_version` | Rebuild the out-of-date artefact (`reproduction.md` §5) |
| `ModuleNotFoundError: claimsense` in a notebook | Package not installed in the kernel | Re-run the install cell; restart the kernel |
| Kaggle: "GPU quota exceeded" | Weekly quota used | Switch to Colab (§6) or wait for the reset; log the gap in the PR |
| Kaggle: data hash mismatch on start | Wrong dataset version attached | Attach the dataset whose name matches `data/processed/LATEST` |
| Colab disconnects mid-run | Idle or usage limit | Re-run with `resume=True`; checkpoints are on Drive |
| `pre-commit` blocks a commit "PDF or raw data path" | Guard hook working as intended | Unstage the file; data is never committed |
