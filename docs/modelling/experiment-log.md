# ClaimSense — Experiment Log

> The index of every modelling run from PR 9 to PR 13: what each run tried, where its full record lives in the tracker, and what was decided because of it. The tracker holds the numbers; this file holds the story, so a reviewer can follow the path from the first baseline to the shipped model without opening the tracker.

**Author:** Diya Shrivastava · **Owning PR:** 9 (created) → 10, 11, 12, 13 (rows added) · **Status:** Planned

**Related:** FR-10, FR-11, NFR-05, `baselines.md`, `finetuning-spec.md`, `calibration.md`, `retrieval-design.md`, `prompt-spec.md`.

---

## 1. Tracker choice

| Option | Pros | Cons | Decision |
|---|---|---|---|
| **MLflow, local file store** (`mlruns/`) | Free, no account, works offline on Kaggle; data never leaves your machines | Basic UI; runs from Kaggle must be copied back | **Default** |
| Weights & Biases (free personal tier) | Good UI, easy sharing, live charts | Run data goes to a third-party service | Optional mirror, metrics only |

Whichever is used, the **run ID** from the tracker is the identifier everywhere else (`meta.json`, `model_version` in `PredictionResult`, PR descriptions).

From Kaggle: write to `/kaggle/working/mlruns/`, download it at the end of the session, and merge into the repo's `mlruns/` with `python -m claimsense.tracking import-runs <dir>`.

`mlruns/` is git-ignored. This file and the exported CSV (§5) are committed.

---

## 2. Naming

| Thing | Pattern | Example |
|---|---|---|
| Experiment | `pr<NN>-<topic>` | `pr09-baselines`, `pr11-lora`, `pr12-calibration`, `pr13-retrieval` |
| Run name | `<model>-<variant>-s<seed>` | `modernbert-r16-lr2e4-s42` |
| Log row ID | `E-<NNN>`, in order | `E-014` |

---

## 3. What every run logs

| Kind | Content |
|---|---|
| **Params** | The full resolved config (every key that affected the run, not only the ones changed) |
| **Tags** | `pr`, `git_sha`, `dataset_version`, `seed`, `base_model`, `base_model_revision`, `prompt_id` (LLM runs), `host`, `gpu`, `status_note` |
| **Metrics** | `val_macro_f1` (+ CI bounds), `val_f1_<class>`, `val_pr_auc_any_payment`, `val_accuracy`, `val_ece`, `val_brier`, `train_minutes`, `gpu_hours`, `parse_failures` (LLM) |
| **Artefacts** | Resolved `config.yaml`, `pip freeze`, val predictions (`doc_id` + class probabilities only), confusion matrix PNG, training curves PNG |

### Never logged

- `facts_text`, `findings_text` or any document text. Predictions are logged by `doc_id` only. This keeps the tracker safe to mirror to W&B.
- Anything from the `test` split before the PR 12 gate. A tracking helper refuses metric names starting with `test_` unless called from the evaluation command (L3).

---

## 4. Rules

1. **Every run is kept.** Crashed or bad runs stay with status `FAILED` or a `status_note`; nothing is deleted. Deleting unflattering runs is how a project fools itself.
2. **One row per decision, not per run.** A 12-config search is one row with the best run linked; the full list stays in the tracker.
3. **"What it tried" is written before the result is known**, as a one-line hypothesis. The "Decision" column is written after.
4. **Numbers are copied by the export script**, never typed by hand (§5).
5. Every PR from 9 to 13 adds its rows in the same PR.

---

## 5. Keeping the index current

```bash
python -m claimsense.tracking export-index --out docs/modelling/experiment-index.csv
```

The script fills the metric columns from the tracker by run ID. The columns *What it tried* and *Decision / note* are edited by hand in the table below; the script leaves them alone.

---

## 6. Run index

Dataset version: `v________` (all rows unless stated). Metrics are on **val**. Planned rows are listed now so the order of work is fixed before any results exist.

| ID | Date | PR | Run ID | Model / config | What it tried | Val macro-F1 | Val PR-AUC | Val ECE | Decision / note |
|---|---|---|---|---|---|---|---|---|---|
| E-001 | | 9 | | B1 majority (prior) | Floor | | | | |
| E-002 | | 9 | | B2 rules (reason × source, backoff) | Does the stated reason alone predict the outcome? | | | | |
| E-003 | | 9 | | B3 TF-IDF + LR, C grid | Classic text baseline; inspect top terms for L2 words | | | | |
| E-004 | | 10 | | B4 bge-small + LR, chunk-mean | Do semantic features beat word counts? | | | | |
| E-005 | | 10 | | B5 zero-shot, P-ZS-v1 | Is prompting alone competitive? | | | | |
| E-006 | | 11 | | Pilot: ModernBERT-base, r16, 2 ep | Is the primary candidate trainable and fast enough on CPU? | | | | |
| E-007 | | 11 | | Pilot: DeBERTa-v3-base, r16, 2 ep | Fallback comparison | | | | |
| E-008 | | 11 | | Search: 12 configs × seed 13 | Best `r` / LR / class-weight combination | | | | |
| E-009 | | 11 | | Final: top-2 configs × 3 seeds | Seed-averaged result for "beats every baseline" | | | | |
| E-010 | | 11 | | Ablation: country prefix | Does knowing the jurisdiction help? | | | | |
| E-011 | | 11 | | Ablation: max length 512 vs 1,024 | Cost of truncation | | | | |
| E-012 | | 11 | | Ablation: lexicon masked | Size of L2 effect (feeds PR 14) | | | | |
| E-013 | | 12 | | Temperature scaling on shipped model | Does one parameter fix calibration? | | | | |
| E-014 | | 12 | | Isotonic (one-vs-rest) | Is a flexible calibrator worth its variance? | | | | |
| E-015 | | 13 | | Encoder comparison for retrieval | Best precedent topic match @5 on val | | — | — | |
| E-016 | | 13 | | k sweep {3, 5, 8, 10} | Explanation quality vs prompt length | | — | — | |
| E-017 | | 13 | | NLI threshold sweep on dev set | Precision of kept sentences ≥ 0.95 | | — | — | |

Add rows below as work happens. Rows for unplanned runs are fine; mark them `(unplanned)` in *What it tried*.

---

## 7. Reproducing a logged run

1. `git checkout <git_sha>` from the run's tags.
2. Make sure `data/processed/LATEST` points to the run's `dataset_version` (or pull it from the private DVC remote).
3. Re-run with the logged config: `python -m claimsense.models.<module> --config <downloaded config.yaml>`.
4. Compare val metrics. Baselines must match exactly; GPU fine-tuning runs must fall within the 3-seed spread.

---

## 8. Summary for the README (filled at PR 18)

| Stage | Best run | Val macro-F1 | Note |
|---|---|---|---|
| Best baseline | | | |
| Fine-tuned (3-seed mean ± sd) | | | |
| After calibration | | (unchanged for temperature scaling) | ECE: |
