# Changelog

All notable changes to ClaimSense are recorded here, **one entry per merged PR**.

The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Before v1.0 the minor number equals the PR number (`0.<PR>.0`), so every PR maps to exactly one version. Patch versions (`0.<PR>.1`) are only for fixes to an already-merged PR.

## How to add an entry

1. In your PR branch, add your changes under **[Unreleased]** using only these headings: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`, plus the project-specific `Data`, `Model` and `Docs` headings.
2. End each bullet with the requirement or risk IDs it touches, e.g. `(FR-06, R5)`.
3. On merge, rename **[Unreleased]** to `[0.<PR>.0] — YYYY-MM-DD — PR <n> · <title>` and open a fresh empty **[Unreleased]** above it.
4. Record **every** new dataset version under `Data` with its hash, and every shipped model under `Model` with its run ID. A data or model change without a changelog line fails review.
5. Never put metrics in a changelog bullet that are not in `reports/metrics.json` for that commit.

CI check `changelog-updated` fails a PR that changes `src/`, `config.yaml`, `data/` rules or `models/` without touching this file.

---

## [Unreleased]

### Added
- Repo scaffold, config, CI, e2e harness. (NFR-05, NFR-10)
- Source audit: decision table per source, `collect` config with the source registry, and the `gitignore-covers-data` guard rule. (NFR-08, NFR-09, R2)

---

## [0.1.0] — ⟨YYYY-MM-DD⟩ — PR 1 · Repo scaffold

### Added
- `src/claimsense/` package layout with empty sub-packages: `collect`, `parse`, `dataset`, `models`, `retrieve`, `explain`, `pipeline`, `eval`, `app`. (NFR-05)
- `pyproject.toml` (Python 3.11), `uv.lock`, exported `requirements-lock.txt`, CPU-only PyTorch index override. (NFR-05)
- Pre-commit with ruff, black and the data/PDF guard hook that blocks `*.pdf` and `data/raw/`. (NFR-10, P-R5)
- pytest with `pytest-socket` (no network in tests) and a placeholder test. (NFR-10)
- GitHub Actions CI: lint, test and `guard` jobs on Ubuntu, Python 3.11. (NFR-10)
- `config.yaml` with every section stubbed and `.env.example`.
- `Makefile` targets: `lint`, `fmt`, `test`.
- `README.md` stub with the disclaimer, `LICENSE` (MIT, code only), `CHANGELOG.md`.

### Security
- `.gitignore` covers `data/`, `.env`, `mlruns/`, `index/`, `.venv/`.

---

<!--
Planned version map (from docs/planning/pr-plan.md). Delete each line when its entry is written.

0.2.0   PR 2   Source audit                         docs/data-sources
0.3.0   PR 3   India collector (risk checkpoint R1)  feat/collect-cioins
0.4.0   PR 4   UK + Ireland collectors               feat/collect-fos-fspo
0.5.0   PR 5   Parse and segment                     feat/parse-segment
0.6.0   PR 6   Labels, anonymisation, leak probes    feat/label-anonymise
0.7.0   PR 7   Dataset build — Data: dataset v________ frozen   feat/dataset-v1
0.8.0   PR 8   EDA notebook                          analysis/eda
0.9.0   PR 9   Classic baselines                     feat/baselines
0.10.0  PR 10  Embedding classifier + zero-shot LLM  feat/embeddings-zeroshot
0.11.0  PR 11  LoRA fine-tune — Model: run ID        feat/lora-finetune
0.12.0  PR 12  Calibration                           feat/calibration
0.13.0  PR 13  Precedent retrieval + cited explanations  feat/retrieve-explain
0.14.0  PR 14  Evaluation report                     eval/report
0.15.0  PR 15  Error analysis and fairness           eval/errors-fairness
0.16.0  PR 16  Inference pipeline                    feat/pipeline
0.17.0  PR 17  Streamlit app                         feat/app
1.0.0   PR 18  Docs and release (tag v1.0.0)         release/v1.0

Entry template:

## [0.N.0] — YYYY-MM-DD — PR N · Title

### Added
- … (FR-xx, R-x)

### Data
- Dataset `vxxxxxxxx` built from manifests … ; parent `v…`; reason: …

### Model
- Run `…`, base `answerdotai/ModernBERT-base@<rev>`, dataset `v…`, val macro-F1 … (3-seed mean ± sd)

### Docs
- …
-->

[Unreleased]: https://github.com/Inquisitiveshri34/claimsense/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Inquisitiveshri34/claimsense/releases/tag/v0.1.0
