# PR 15 · Error analysis and fairness

| | |
|---|---|
| **Branch** | `eval/errors-fairness` |
| **Depends on** | PR 14 |
| **Covers** | NFR-04(b), NFR-11 · **Risks** R10, R13 |
| **Read first** | `docs/evaluation/error-taxonomy.md`, `docs/evaluation/fairness-analysis-plan.md`, `docs/evaluation/faithfulness-rubric.md`, `docs/data/manual-audit-protocol.md` (A5, A6), `reports/error-analysis.md` |
| **Done when** | Failure modes are written up with counts; fairness slices and explanation faithfulness are in the report |

---

## 1. Goal

Know how and for whom the model fails, and how faithful the explanations are, using small hand-labelled audits whose files contain ids and judgements only.

## 2. Files to add

| File | Contents |
|---|---|
| `src/claimsense/evaluate/errors.py` | `sample_errors(n=50, seed=eval.audit_seeds.errors)` → `audits/A5-errors.csv` template (doc ids, true/pred, probability, reason — no text); `load_a5(path)` validates categories against `error-taxonomy.md`; `summarise_a5` counts per category |
| `src/claimsense/evaluate/fairness.py` | Slices by insurer type and claim-size band (bands from the plan); metric + CI per slice; gap vs overall; "too few" for n < `min_slice_n` |
| `src/claimsense/evaluate/faithfulness.py` | `sample_a6(n=40, seed=eval.audit_seeds.A5A6)` → `audits/A6-faithfulness.csv` (query id, sentence id, cited ids — the reviewer reads text locally via a helper that prints it to the terminal, never into the CSV); `load_a6` schema; faithfulness rate; two-rater agreement (Cohen's κ) when a second column is present |
| `notebooks/error_analysis.ipynb` | Calls the module; aggregates only |
| `tests/unit/test_errors_audit.py`, `tests/unit/test_fairness.py`, `tests/unit/test_faithfulness_loader.py` | See §4 |

## 3. Files to modify

`src/claimsense/evaluate/report.py` (sections: fairness slices, A5 summary if file present, A6 faithfulness if present, else "audit pending"), `reports/error-analysis.md` (generated tables + Diya's prose), `Makefile` (`audit-sample-a5`, `audit-sample-a6`), `scripts/ci_guard.sh` (rule: files in `audits/` contain no field longer than 200 chars), `CHANGELOG.md`.

## 4. Tests to write

- **`test_errors_audit.py`**: sampler deterministic; only misclassified test rows; CSV has no text; unknown category → validation error; counts sum to n.
- **`test_fairness.py`**: slice counts sum to total; small slices marked; known toy data → known gap.
- **`test_faithfulness_loader.py`**: schema; faithfulness rate on a toy file; κ on a hand-computed 2-rater example.

## 5. E2E tests

**`tests/e2e/test_e2e_15_errors_fairness.py`**:
- On the world: `sample_errors` draws only rows that the **world's** calibrated smoke model got wrong (cross-check with `collect_predictions`).
- Fabricate a completed A5/A6 file for the world (categories from the taxonomy, judgements from ground truth) → `make report` includes the A5 counts and A6 rate; without the files the report says "audit pending" instead of failing.
- Execute `notebooks/error_analysis.ipynb` on the world without errors.
- Earlier e2e files pass unchanged.

## 6. Definition of done

`make pr-check` → ALL CHECKS PASSED; raise the floor.

## 7. Manual checks (Diya)

- [ ] `make audit-sample-a5`; categorise all 50 in the CSV; counts in `reports/error-analysis.md` sum to 50.
- [ ] `make audit-sample-a6`; judge 40 sentences per `faithfulness-rubric.md`.
- [ ] `make report`; review fairness slices and write the prose findings.
