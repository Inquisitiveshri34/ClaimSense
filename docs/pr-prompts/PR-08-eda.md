# PR 8 · EDA notebook

| | |
|---|---|
| **Branch** | `analysis/eda` |
| **Depends on** | PR 7 (+ tag `eval-protocol-v1`) |
| **Covers** | — · **Risks** R7, R13 |
| **Read first** | `reports/eda-findings.md` (planned structure), `docs/data/dataset-versioning.md`, `docs/evaluation/fairness-analysis-plan.md`, `docs/architecture/data-schema.md` |
| **Done when** | The notebook renders end to end and findings are written up |

---

## 1. Goal

Understand the data before modelling. All analysis logic lives in a tested module; the notebook only calls it and plots, so it can run on the real data **and** on the e2e world.

## 2. Files to add

| File | Contents |
|---|---|
| `src/claimsense/evaluate/eda.py` | Pure functions over the processed splits: outcome rate by source / year / insurer type / rejection reason; text-length distribution (chars and tokenizer-free word counts); outcome-word lexicon rate by label; class balance per split; `summary(version) -> dict` |
| `notebooks/eda.ipynb` | Reads `CLAIMSENSE_DATA_DIR` (default real data); calls `eda.py`; saves figures to `reports_dir()/figures/eda_*.png`; prints **aggregates only, never record text** |
| `tests/unit/test_eda.py` | See §4 |
| `tests/integration/test_eda_notebook.py` | `local_data`: executes the notebook with `nbclient` on the real dataset |

## 3. Files to modify

`reports/eda-findings.md` (filled from the real run), `pyproject.toml` (`dev`: `nbclient`, `nbformat`, `ipykernel`, `matplotlib`), `Makefile` (`eda`: execute notebook in place), `scripts/ci_guard.sh` (remove the "tag missing" allowance from PR 7; new rule `notebook-no-text`: committed notebooks' outputs contain no string longer than 300 chars and no `facts_text` / `findings` field dumps), `CHANGELOG.md`.

## 4. Tests to write

- **`test_eda.py`** on the mini dataset: rates sum to 1 per group; group counts match a hand count; empty group handled; function outputs contain no free text from records (only numbers/categories).
- **`test_eda_notebook.py`** (`local_data`): runs without error; every figure file listed in `reports/eda-findings.md` exists.

## 5. E2E tests

**`tests/e2e/test_e2e_08_eda.py`**:
- Execute `notebooks/eda.ipynb` with `nbclient` on the world (env vars point to the world) → no errors, figures written under the world's reports dir (not the repo's).
- `eda.summary()` on the world shows the corpus's planted signal (e.g. upheld rate higher for the "diagnosed after inception" reason) — proves the dataset carried the signal through every earlier stage.

## 6. Definition of done

`make pr-check` → ALL CHECKS PASSED; raise the floor.

## 7. Manual checks (Diya)

- [ ] `make eda` on real data; write the findings in `reports/eda-findings.md` (majority-class rate, source imbalance, length → informs `finetune.max_length`).
- [ ] Open the notebook in git diff: no case text in any output cell.
