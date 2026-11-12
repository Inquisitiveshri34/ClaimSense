# ClaimSense — Reproduction

> How to go from a fresh clone to the metrics reported in the README and the evaluation report with one command, what "reproduced" means for each number (exact match or a stated tolerance), what a reader without access to the data can still verify, and how the PR 18 release gate is run and recorded.

**Author:** Diya Shrivastava · **Owning PR:** 18 (script, reference results, release gate); builds on PR 7 (dataset hash), PR 11 (seeds, `meta.json`), PR 14 (`make report`) · **Status:** Planned

**Related:** NFR-05 (reproducibility), FR-09, FR-20, `setup.md`, `configuration.md`, `ci-cd.md` §5, `../data/dataset-versioning.md`, `../data/terms-of-use-audit.md` §6, `../modelling/experiment-log.md` §7, `../modelling/finetuning-spec.md` §7–§8, `../modelling/prompt-spec.md` §6, `../evaluation-protocol.md` §3, §11, `../testing/test-strategy.md` §6.

---

## 1. The claim, stated precisely

> **A fresh clone of the `v1.0.0` tag, given the frozen dataset version and the released model artefacts, regenerates every gated test metric in the README with one command, within the tolerances in §4.**

Three things make this hard, and the design answers each:

| Difficulty | Answer |
|---|---|
| The dataset is **not redistributable** for all sources (`terms-of-use-audit.md` §6) | Reproduction is tiered (§2). The dataset is identified by a content hash, so anyone who rebuilds it can prove they have the same one |
| GPU fine-tuning is **not bit-exact** across runs | Two levels: re-scoring the **released** adapter is exact on CPU; **retraining** must land inside the published 3-seed spread |
| Hosted LLMs are **retired and drift** | Explanation outputs are cached by request hash; the cache is part of the release bundle for authorised reproducers, and drift is measured once and reported (`prompt-spec.md` §6) |

---

## 2. Reproduction tiers

| Tier | Who can run it | Needs | Proves | Command |
|---|---|---|---|---|
| **T0 · Code** | Anyone | Fresh clone only | The code, tests, leak probes and report builder all work | `make reproduce-t0` |
| **T1 · Results** | Anyone with the frozen dataset (the author; anyone given it privately; anyone who rebuilds it in T2) | `data/processed/<v1 hash>/` + released artefacts | **The reported test metrics** — the PR 18 gate | `make reproduce` |
| **T2 · Pipeline** | Anyone, for sources whose terms allow collection | Network, ~1 day of polite collection, free GPU | The data and model can be rebuilt from the public sources | `make reproduce-t2` (staged; §6) |

**T1 is the release gate.** T0 runs in CI on every PR. T2 is documented and was run once by the author for the sources that were cleared; its outcome is reported honestly in §6.4 because the source websites change over time.

---

## 3. Tier 1 — one command

### 3.1 Prerequisites

1. A clean environment: a new WSL2 distro, a new user account, or a container:
   ```bash
   docker run --rm -it -v "$PWD/inputs:/inputs:ro" ubuntu:24.04 bash
   ```
   then the system tools from `setup.md` §2.2. **Do not reuse** the development `.venv`, Hugging Face cache or `mlruns/`; a clean environment is the point.
2. The two inputs, placed outside the clone:

   | Input | Contents | Source |
   |---|---|---|
   | `inputs/processed-<v1 hash>/` | `train.parquet`, `val.parquet`, `test.parquet`, `schema.json`, `build_meta.json` | Private DVC remote (`dvc pull`), or your own T2 rebuild |
   | `inputs/release-v1.0.0/` | `lora-adapter/`, `calibrator.pkl`, `thresholds.json`, `topic_clf.pkl`, `llm_cache/`, `SHA256SUMS` | GitHub Release assets (weights, if published) + private bundle (`llm_cache/`) |

3. No API key is needed: T1 reads explanations from the cache. With a key set, missing cache entries are filled by live calls and the run is labelled `cache_miss` in the output (§4.3).

### 3.2 Run

```bash
git clone --branch v1.0.0 --depth 1 https://github.com/Inquisitiveshri34/claimsense.git
cd claimsense
uv sync --frozen --all-extras
make reproduce DATA=../inputs/processed-<v1 hash> ARTEFACTS=../inputs/release-v1.0.0
```

### 3.3 What `scripts/reproduce.sh` does

| Step | Action | Stops if |
|---|---|---|
| 1 · Environment | Print OS, CPU, RAM, Python, `uv` version; `uv sync --frozen` | Python ≠ 3.11; lock out of date |
| 2 · Code | `make lint` and `make test` (the T0 suite) | Any failure |
| 3 · Dataset identity | Copy data into `data/processed/`, write `LATEST`, **recompute the content hash** from the records (`dataset-versioning.md` §2) | Hash ≠ `dataset_version` in `results/reference.json` |
| 4 · Data gates | `make test-data`: leak probes, PII regex scan, schema, temporal split, cross-split dedup on the real data | Any failure or skip |
| 5 · Artefact identity | Check `SHA256SUMS`; check every artefact's `dataset_version` and `model_run_id` agree (`configuration.md` §4) | Any mismatch |
| 6 · Models | Download base models at the **pinned Hub revisions** from `meta.json`, `index_meta.json` and `config.yaml` | Revision unavailable |
| 7 · Index | `make index`; compare the new `faiss.index` vector checksum and `metadata.parquet` row hash with the reference | Mismatch |
| 8 · Report | `python -m claimsense.eval report --purpose reproduction --out reports/reproduce/` (one logged test-split load, `evaluation-protocol.md` §3) | Report error |
| 9 · Compare | `python -m claimsense.eval compare reports/reproduce/results.json results/reference.json` | Any metric outside tolerance (§4) |
| 10 · Record | Write `reports/reproduce/REPRODUCTION.md`: environment, hashes, the comparison table, pass/fail, total time | — |

Expected wall time on a laptop CPU: under 2 hours, dominated by embedding the index and running the NLI checker over the test explanations.

Exit code is `0` only if every gated metric passes. The script never edits `results/reference.json`.

---

## 4. What "reproduced" means, per number

`results/reference.json` (committed in PR 18) holds every reported number with its CI, the protocol hash, `dataset_version`, the shipped `model_run_id` and the `prompt_id`s used. The compare step applies these tolerances:

### 4.1 Tier 1 tolerances (released artefacts, same data)

| Metric | Gate? | Tolerance | Why |
|---|---|---|---|
| Dataset content hash | ✅ | **Exact** | Defines the data |
| Baselines B1–B4 macro-F1, per-class F1, PR-AUC | ✅ (E1 comparison) | **Exact** to 3 decimals | CPU, seeded, deterministic |
| Baseline B5 (zero-shot) | ✅ (E1 comparison) | **Exact** with a full cache | Read from cache |
| Fine-tuned macro-F1, per-class F1, PR-AUC (E1–E3) | ✅ | ± 0.002 | CPU inference of the merged adapter; tiny float differences across CPUs can flip a near-tie |
| Test ECE, Brier (E4) | ✅ | ± 0.002 | Same |
| Coverage, selective metrics, abstain counts (E5) | — | ± 1 record per code | A near-threshold record may flip |
| Bootstrap CIs | — | ± 0.01 on each bound | Seeded, but depends on point values |
| Earlier-only filter share (E6a) | ✅ | **Exactly 100%** | Correctness property |
| Automatic retrieval proxies (reason match@5, etc.) | — | **Exact** | Exact FAISS search, pinned encoder revision |
| Structural citation check (E7a) | ✅ | **Exactly 100%** | Correctness property |
| Kept-sentence count, NLI scores | — | Exact with a full cache; ± 0.01 on mean entailment | NLI model on CPU |
| A5 / A6 audit results (E6, E7b, E7c) | ✅ | **Recomputed** from the committed audit verdict files, exactly | Manual labels are inputs, not re-judged; the script recomputes the rates and CIs from them |
| Latency p50 / p95 (E8) | ✅ (on reference laptop) | **Not compared**; re-measured and reported with the hardware | Hardware-dependent; the reproducer's numbers are informative only |
| Slice results (§8 of the protocol) | — | Same rules as their metric | — |

A metric outside tolerance fails the run. The fix is to find the cause (§7), never to widen the tolerance after the fact.

### 4.2 Retraining tolerances (T2, or re-running PR 11)

| Metric | Tolerance |
|---|---|
| Val macro-F1 of each retrained seed | Within the published 3-seed **min–max range**, widened by one published standard deviation on each side |
| Test macro-F1 of the retrained median seed | Its 95% bootstrap CI overlaps the reference CI |
| Test ECE after refitting the calibrator | ≤ 0.05 (the gate itself) |
| "Beats every baseline" | Still true on the 3-seed mean |

Retrained results never replace the reference numbers; they are reported beside them.

### 4.3 LLM-dependent numbers

| Situation | Outcome label | Counted as reproduced? |
|---|---|---|
| All P-ZS / P-EX calls served from cache | `cache_full` | Yes, exact |
| Some cache misses, filled by the **same** pinned model ID | `cache_miss` | Yes if within the drift bound measured in PR 14 (re-call of 50 cached items) |
| Pinned model retired | `model_retired` | **No** for B5 and explanation metrics. A new prompt version is needed (`prompt-spec.md` §3); the classifier, calibration and retrieval results are unaffected and still checked |

---

## 5. Rebuilding one artefact

When `predict()` or the script raises `ArtifactMismatchError`, rebuild only what is out of date, in this order (each depends on the one above):

| Out of date | Command | Then also rebuild |
|---|---|---|
| Dataset | `make build` (needs `data/interim/labelled/`) | Everything below |
| Baselines | `python -m claimsense.models.baselines --all` | — |
| Fine-tuned adapter | Kaggle notebook (`setup.md` §5) | Calibrator, thresholds |
| Calibrator | `python -m claimsense.models.calibrate` | Thresholds |
| Topic classifier, thresholds | `python -m claimsense.pipeline tune-thresholds` | — |
| Precedent index | `make index` | — |
| Report | `make report` | — |

`make all-local` runs every CPU step from the dataset down in order; it does not retrain the adapter.

---

## 6. Tier 2 — rebuilding from the public sources

Staged, because collection is slow on purpose (NFR-08) and training needs a GPU.

```bash
make reproduce-t2 STAGE=collect     # per enabled source; resumable; ~hours
make reproduce-t2 STAGE=build       # parse → segment → label → anonymise → dedup → split
make reproduce-t2 STAGE=compare-data
# fine-tune on Kaggle with the three seeds (setup.md §5), copy artefacts back
make reproduce-t2 STAGE=evaluate    # calibrate, tune thresholds, index, report, compare (§4.2)
```

### 6.1 Collection

- Only sources with `enabled: true` in `config.yaml` are collected; enabling a source requires clearing it in `terms-of-use-audit.md` first. Do not enable a source for reproduction that the audit has not cleared.
- Restrict to the reference window: `--to` set to the latest `decision_date` in the reference `build_meta.json`, so decisions published after v1 are not added.

### 6.2 Comparing the rebuilt data

`STAGE=compare-data` compares the rebuilt dataset with the reference **by record**, not only by hash:

| Check | Expected |
|---|---|
| Content hash | Same as reference (ideal) |
| If different: records only in reference / only in rebuild | Listed by `doc_id`, with the funnel stage where they diverge |
| Per-source, per-split, per-label counts | Shown side by side |

### 6.3 Why the hash may differ, and what that means

| Cause | Effect | Still a valid reproduction? |
|---|---|---|
| Publisher removed or replaced decisions | Fewer or different records | Yes, if differences are listed and metrics fall within §4.2 |
| PDF re-rendered by the publisher (new file hash, same text) | Usually none: the hash is over records, not bytes | Yes |
| OCR output differs (different Tesseract build) | A few `facts_text` changes | Yes, if listed; pin Tesseract ≥ 5.0 to reduce this |
| A source was not cleared for you | That source is missing | Partial: report results for the sources you have |

### 6.4 Author's T2 run (filled in PR 18)

| Item | Value |
|---|---|
| Date | |
| Sources collected live | |
| Reference hash / rebuilt hash | |
| Records only in reference / only in rebuild | |
| Retrained seeds val macro-F1 | |
| Within §4.2 tolerances? | |

---

## 7. When a T1 number does not match

| Symptom | Likely cause | Check |
|---|---|---|
| Dataset hash differs | Wrong version copied, or a file was edited | `build_meta.json` `dataset_version`; re-pull from DVC |
| All fine-tuned metrics off by a lot | Wrong base-model revision, wrong label order, or truncation side | `meta.json` revision and `id2label` vs `config.yaml` |
| Fine-tuned off slightly, baselines exact | CPU float differences beyond ± 0.002 | Re-run with `torch.set_num_threads(1)`; report CPU model |
| Baselines off | Library version drift | `uv sync --frozen` was skipped, or a non-locked install |
| E5 abstain counts off by many | `thresholds.json` from another run | Artefact identity step (§3.3 step 5) |
| Retrieval proxies off | Encoder revision differs | `index_meta.json` `encoder_revision` |
| B5 / explanation metrics off | Cache incomplete; provider drift | Output label (§4.3) |
| `test_access.log` shows extra loads | Something other than `eval report` read test | Leakage bug: stop and investigate (`evaluation-protocol.md` §3) |

---

## 8. PR 18 release gate

The release is tagged only after a T1 run in a clean environment passes.

| Evidence in the PR 18 description | Source |
|---|---|
| `REPRODUCTION.md` from the clean run (environment, hashes, comparison table, PASS) | `reports/reproduce/` |
| Full command log | Terminal capture of `make reproduce` |
| The machine used (CPU, RAM, OS) | Step 1 output |
| `results/reference.json` committed and matching the README results table | Diff check in `test_readme_results.py` |
| T2 summary (§6.4) | Author's T2 run |

After the tag, `results/reference.json` is never changed. A later correction is a new release with its own reference file and a note in `CHANGELOG.md`.

---

## 9. Files

```text
scripts/reproduce.sh                 # T1 and the staged T2 driver
results/reference.json               # committed reference numbers (PR 18)
reports/reproduce/                   # generated; git-ignored except REPRODUCTION.md attached to the release
src/claimsense/eval/compare.py       # tolerance table (§4) as code
tests/integration/test_reproduce_t0.py   # T0 in CI: reproduce.sh on the mini-dataset with stub artefacts
tests/unit/test_compare_tolerances.py    # inside/outside tolerance cases; tolerances read from one table
```
