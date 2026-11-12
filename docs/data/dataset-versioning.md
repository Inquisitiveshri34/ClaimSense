# ClaimSense — Dataset Versioning

> How a processed dataset version is built, identified, frozen and replaced: the content hash, the optional DVC layer, the temporal split rules, what goes in each version's data card, and exactly which changes force a new version.

**Author:** Diya Shrivastava · **Owning PR:** 7 · **Status:** Planned

**Related:** `data-schema.md` §4, `data-flow.md` Stage 5, `leakage-contract.md` (L3, L4), FR-08, FR-09, NFR-05.

---

## 1. What a version is

A version is one frozen set of `train.parquet`, `val.parquet`, `test.parquet` plus its data card, identified by an 8-character content hash:

```text
data/processed/
├── LATEST                 # "v3f9a1c2e"
└── v3f9a1c2e/
    ├── train.parquet
    ├── val.parquet
    ├── test.parquet
    ├── DATA_CARD.md
    ├── funnel.csv
    ├── schema.json
    └── build_meta.json
```

Once written, a version directory is **never edited**. Fixes produce a new version.

---

## 2. The content hash

```text
dataset_version = "v" + sha256(canonical_records)[:8]
```

- `canonical_records` = all records from all three splits, sorted by `(decision_date, doc_id)`, each serialised as JSON with sorted keys, UTF-8, no whitespace, `dataset_version` field excluded; joined by `\n`.
- Because `split` is a field in each record, changing the split rules changes the hash.
- Parquet bytes are **not** hashed (compression and writer versions vary); the records are.
- Rebuilding from the same interim inputs and config must give the same hash (FR-09b). A test rebuilds twice in CI on fixtures and compares.

### `build_meta.json`

```json
{
  "dataset_version": "v3f9a1c2e",
  "built_at": "2027-01-10T08:00:00Z",
  "code_commit": "<git sha>",
  "config_hash": "<sha256 of the data sections of config.yaml>",
  "manifest_snapshot": {"cioins": 0, "fos": 0, "fspo": 0},
  "rules": {"segment": {"fos": "fos/v1", "fspo": "fspo/v1", "cioins": "per-office"}, "label": "v1", "anonymise": "v1"},
  "dedup": {"method": "minhash", "num_perm": 128, "shingle": 5, "threshold": 0.8},
  "split": {"train_end": "2023-12-31", "val_end": "2024-12-31"},
  "parent_version": null
}
```

---

## 3. Hash or DVC

| Option | Use when | What it adds |
|---|---|---|
| **Content hash only** (default) | Solo work, data never leaves the laptop | Zero setup; identity and reproducibility check |
| **Hash + DVC** | Data must move between machines (e.g. laptop → Kaggle for training) | `dvc push/pull` to a private remote (Google Drive or a private bucket), `dvc.lock` pins inputs and outputs per stage |

If DVC is used: track `data/processed/<version>/` with `dvc add`, keep the remote **private** (the data may not be redistributable, see `terms-of-use-audit.md` §6), and never point a DVC remote at a public location. The content hash remains the version ID either way; DVC is transport, not identity.

---

## 4. When a new version is cut

| Change | New version? |
|---|---|
| New documents collected (any source) | **Yes** |
| Segmentation rule version bump | **Yes** |
| Label rule or exclusion change | **Yes** |
| Anonymiser change (detector, token, allowlist) | **Yes** |
| Dedup threshold or method change | **Yes** |
| Split dates change | **Yes** — and all models must be retrained and re-evaluated |
| Enum value added/renamed (`data-schema.md` §1) | **Yes** |
| New column (e.g. `insurer_name`) | **Yes** |
| FOS health-keyword list change | **Yes** |
| Code refactor with identical output | No (CI hash check proves it) |
| Data card wording fix only | No — edit is allowed in the card's *Errata* section only |

### Cadence

v1 is frozen at the end of PR 7. After that, a new version is cut only for a **correctness** fix (a PII hit, a leak, a labelling bug). New data is not added during v1 development; it waits for v2 (scope V2-09). Every model artefact records the `dataset_version` it was trained on; `predict()` refuses to run on a mismatch (`pipeline-interface.md` §5).

---

## 5. Split rules (L3)

| Split | `decision_date` |
|---|---|
| `train` | ≤ 2023-12-31 |
| `val` | 2024-01-01 … 2024-12-31 |
| `test` | ≥ 2025-01-01 |

- Assigned once, at build time, by `dataset/split.py`, and stored in the `split` column.
- Training, tuning, calibration and threshold selection read `train`/`val` only; only the report command reads `test`.
- **Sparse-split rule:** if any source has fewer than 30 records in `val` or `test`, the version is still built, but the data card flags it and the evaluation report gives that source's metrics with a "small sample" warning. Split dates are **not** moved to fix it (that would be choosing the test set by looking at it).

---

## 6. Dedup before split (L4)

1. MinHash (128 permutations, 5-word shingles) on `facts_text` of **all** labelled records.
2. Cluster pairs above the threshold chosen in audit A4 (`manual-audit-protocol.md` §6; starting value 0.8).
3. Keep the **earliest** record per cluster (ties → lowest `doc_id`), so no copy of a case can survive in a later split.
4. Post-split test: no cross-split pair above threshold (FR-08b).
5. Removed IDs and their kept partner go to `funnel.csv` and `dedup_log.csv` (local).

---

## 7. Data card (`DATA_CARD.md`)

Generated by `dataset/datacard.py`, then completed by hand in the marked sections.

| Section | Contents | Generated? |
|---|---|---|
| Identity | Version, build date, code commit, parent version | ✅ |
| Sources and terms | Per source: date range, count, licence/permission status, attribution wording | Counts ✅; terms from `terms-of-use-audit.md` |
| Funnel | Counts at each stage with drop reasons (`data-flow.md` §3) | ✅ |
| Splits | Counts per split × source × label | ✅ |
| Class balance | Label shares per source; flag any class < 10% (R7) | ✅ |
| Attributes | Distributions of rejection reason, insurer type, claim band, year | ✅ |
| Quality | Segmentation (A1), label (A2) and PII (A3) audit results | From `audit_index.csv` |
| Anonymisation | Method summary and token list | Link to `anonymisation-spec.md` |
| Leakage | Lexicon rate per label (L2) | ✅ |
| Known gaps | Selection bias, jurisdiction mismatch, missing offices, small splits | ✍️ |
| Intended use / not for | Research and the ClaimSense app; not legal advice; not for decisions about individuals | ✍️ |
| Errata | Wording corrections after freeze | ✍️ |

---

## 8. Version log

| Version | Date | Parent | Why cut | Records (train / val / test) | Notes |
|---|---|---|---|---|---|
| — | — | — | v1 to be built in PR 7 | — | — |
