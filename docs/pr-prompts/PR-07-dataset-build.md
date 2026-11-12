# PR 7 · Dataset build

| | |
|---|---|
| **Branch** | `feat/dataset-v1` |
| **Depends on** | PR 6 |
| **Covers** | FR-08, FR-09, NFR-05 · **Risks** R7 |
| **Read first** | `docs/data/dataset-versioning.md`, `docs/architecture/data-schema.md` §4, `docs/testing/leak-probe-tests.md` (split + dedup), `docs/testing/test-fixtures.md` §6–§7, `docs/evaluation/evaluation-protocol.md` §2, `docs/operations/configuration.md` §3.4 |
| **Done when** | Dataset v1 is frozen with a version hash; rebuilding gives the same hash |

---

## 1. Goal

One command builds a versioned, leakage-safe dataset: deduplicated across time, split strictly by decision date, with a data card. The evaluation protocol is frozen with a git tag before any model is trained.

## 2. Files to add

| File | Contents |
|---|---|
| `src/claimsense/dataset/dedup.py` | MinHash (`num_perm`, `shingle`, `threshold` from config) over `facts_text`; clusters; keep the **earliest** decision per cluster; returns kept ids + `dedup_report` |
| `src/claimsense/dataset/split.py` | `train ≤ split.train_end`, `val ≤ split.val_end`, `test` after; boundary dates inclusive per spec; flags sources with < `sparse_split_min` in val/test |
| `src/claimsense/dataset/build.py` | `build(cfg) -> BuildResult`: labelled records → drop `EXCLUDE` → dedup → split → write `processed_dir(version)/{train,val,test}.parquet`, `schema.json`, `build_meta.json` (`dataset_version`, `config_hash`, rule versions, split dates, counts, input content hash); `version` = hash of (config_hash + sorted record content hashes); writes `processed_root()/LATEST`. Deterministic: same inputs → identical bytes (sorted rows, fixed parquet writer settings) |
| `src/claimsense/dataset/datacard.py` | Renders `DATA_CARD.md` tables from `build_meta.json` (counts per source × split × label) |
| `src/claimsense/dataset/__main__.py` | `python -m claimsense.dataset build`, `datacard`, `audit-dedup --n 30` (A4 sample: ids + similarity only) |
| `src/claimsense/dataset/loader.py` | `load_split(name, version=None) -> DataFrame` validated against `schema.json`; used by every later PR |
| `tests/fixtures/leak/split_clean.parquet`, `split_planted.parquet`, `dedup_clean.jsonl`, `dedup_planted.jsonl` | Per `test-fixtures.md` §6 |
| `tests/fixtures/dataset/mini/` + `scripts/fixtures/make_mini_dataset.py` | 60 synthetic processed records (20/split, all labels, sources and reasons) |
| `tests/integration/test_dataset_build.py`, `tests/leak/test_temporal_split.py`, `tests/leak/test_cross_split_dedup.py`, `tests/unit/test_loader.py` | See §4 |
| `tests/e2e/test_e2e_99_contracts.py` | See §5 |

## 3. Files to modify

`config.yaml` (`dataset`; **V**), `config.py`, `pyproject.toml` (`datasketch`, `pyarrow`, `pandas`), `Makefile` (`build` = parse → label → dataset build, `datacard`), `DATA_CARD.md` (generated section markers), `scripts/ci_guard.sh` (rule `protocol-frozen`: `git diff --quiet eval-protocol-v1 -- docs/evaluation/evaluation-protocol.md` or a new row in its deviations log; skip with PASS if the tag does not exist yet **only in this PR**), `scripts/pr_check.sh` (step 8 now runs `make test-data` when `data/processed/LATEST` exists), `tests/fixtures/FIXTURES.yaml`, `CHANGELOG.md`.

## 4. Tests to write

- **`test_dataset_build.py`** (on the mini labelled input): build twice → same `dataset_version` and byte-identical parquet; `build_meta.json` has all fields; changing a **V** key → new version; `LATEST` points to the new dir.
- **`test_temporal_split.py`** (marker `leak`): boundary dates land in the right split; planted 2025 record in train → FAIL naming the record; `local_data` variant on the real `LATEST`.
- **`test_cross_split_dedup.py`** (marker `leak`): planted exact copy train/test → FAIL; near copy val/test → FAIL; cluster where the later copy was kept → FAIL; `local_data` variant.
- **`test_loader.py`**: schema mismatch raises; missing version raises `ArtifactNotFoundError`.

## 5. E2E tests

Add to `tests/e2e/corpus.py`: 4 near-duplicate decisions (same facts, small edits) crossing years, so dedup has work.

`stages.py`: `run_build(world) -> BuildResult` (→ `run_label`).

**`tests/e2e/test_e2e_07_dataset.py`**:
- Build succeeds; train/val/test all non-empty with all 3 labels in train.
- Every near-duplicate cluster from the corpus keeps exactly the earliest member.
- All leak probes (incl. split + dedup) PASS on the built dataset.
- Rebuilding in the same world → same version; record counts == labelled − EXCLUDE − dedup removals.

**`tests/e2e/test_e2e_99_contracts.py`** (extended by later PRs): for every artefact that exists in the world, its recorded `dataset_version` equals `LATEST`. Today: `build_meta.json` only.

## 6. Definition of done

`make pr-check` → ALL CHECKS PASSED; raise the floor.

## 7. Manual checks (Diya)

- [ ] Real data: `make build` twice → same hash. Paste both. `make test-data` → all pass (no skips).
- [ ] **Audit A4:** `python -m claimsense.dataset audit-dedup --n 30`; check pairs; confirm or change `dataset.dedup.threshold` (change → rebuild → new hash).
- [ ] `make datacard`; review `DATA_CARD.md`.
- [ ] After merge: `git tag eval-protocol-v1 && git push origin eval-protocol-v1` (and remove the "skip if tag missing" branch of the guard rule in PR 8).
