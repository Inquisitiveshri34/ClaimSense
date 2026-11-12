# ClaimSense — Data Schema

> Field-level definitions for every stored dataset: the **download manifest** (SQLite), the **processed record** (Parquet), the **precedent index** entry, and the logs that sit beside them. Types, constraints and examples are fixed here so collectors, the dataset builder and tests all validate against one source of truth.

**Author:** Diya Shrivastava · **Owning PR:** 3 (manifest), 4 (shared schema across sources), 7 (processed), 13 (index) · **Status:** Planned

**Related:** `../05-project-description.md` §6, `data-flow.md`, `../04-data-sources.md`.

---

## 1. Enumerations

Defined once in `src/claimsense/schema.py` and imported everywhere.

| Enum | Values |
|---|---|
| `Source` | `cioins`, `fos`, `fspo` |
| `Country` | `IN`, `GB`, `IE` (derived from `source`) |
| `Product` | `individual_mediclaim`, `group_mediclaim`, `overseas_mediclaim`, `private_health` |
| `Label` | `upheld`, `partially_upheld`, `rejected` |
| `InsurerType` | `public`, `private`, `standalone_health` |
| `RejectionReason` | `non_disclosure`, `waiting_period`, `exclusion`, `not_medically_necessary`, `documentation`, `other` |
| `ClaimAmountBand` | `lt_50k`, `50k_2l`, `2l_5l`, `gt_5l`, `unknown` (INR; GBP/EUR converted at a fixed rate stored in `config.yaml`) |
| `Split` | `train`, `val`, `test` |

Changing an enum value changes the dataset hash and requires a new dataset version.

---

## 2. Manifest — `data/manifests/manifest.sqlite` `[PR 3, 4]`

One row per downloaded document. One table shared by all three sources (FR-02c).

| Field | Type | Required | Constraint | Example |
|---|---|---|---|---|
| `doc_id` | TEXT | ✅ | Primary key; `<source>-<yyyy>-<mm>-<local id>` | `cioins-2023-05-1004-0056` |
| `source` | TEXT | ✅ | `Source` enum | `cioins` |
| `url` | TEXT | ✅ | Absolute https URL; local traceability only | original document URL |
| `decision_date` | TEXT | ✅ | ISO date `YYYY-MM-DD` | `2023-05-12` |
| `insurer` | TEXT | ✅ | Name as published; normalised later | insurer name |
| `product` | TEXT | ✅ | `Product` enum | `individual_mediclaim` |
| `outcome_raw` | TEXT | ✅ | Source wording, untouched | `Complaint allowed` |
| `office` | TEXT | ❌ | CIOINS only | `Ahmedabad` |
| `file_path` | TEXT | ✅ | Relative to `data/raw/` | `cioins/cioins-2023-05-1004-0056.pdf` |
| `file_sha256` | TEXT | ✅ | 64 hex chars; unique | — |
| `mime_type` | TEXT | ✅ | `application/pdf` or `text/html` | `application/pdf` |
| `fetched_at` | TEXT | ✅ | ISO datetime, UTC | `2026-11-20T09:14:03Z` |
| `collector_version` | TEXT | ✅ | Package version that fetched it | `0.3.0` |

### DDL

```sql
CREATE TABLE IF NOT EXISTS manifest (
    doc_id            TEXT PRIMARY KEY,
    source            TEXT NOT NULL CHECK (source IN ('cioins','fos','fspo')),
    url               TEXT NOT NULL,
    decision_date     TEXT NOT NULL CHECK (decision_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    insurer           TEXT NOT NULL,
    product           TEXT NOT NULL CHECK (product IN
                        ('individual_mediclaim','group_mediclaim','overseas_mediclaim','private_health')),
    outcome_raw       TEXT NOT NULL,
    office            TEXT,
    file_path         TEXT NOT NULL,
    file_sha256       TEXT NOT NULL UNIQUE CHECK (length(file_sha256) = 64),
    mime_type         TEXT NOT NULL,
    fetched_at        TEXT NOT NULL,
    collector_version TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_manifest_source_date ON manifest (source, decision_date);

-- Pages visited but not stored (filtered out, failed, skipped), so re-runs know what was seen.
CREATE TABLE IF NOT EXISTS crawl_log (
    url         TEXT PRIMARY KEY,
    source      TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('stored','filtered','failed','duplicate')),
    reason      TEXT,
    seen_at     TEXT NOT NULL
);
```

`url` and `crawl_log` stay local: they link back to named individuals' decisions.

---

## 3. Interim files — `data/interim/` `[PR 5, 6]`

Git-ignored. JSON per document, so a single file can be inspected by hand during the PR 5 audit.

### `segments/<doc_id>.json`

```json
{
  "doc_id": "cioins-2023-05-1004-0056",
  "marker_rule": "cioins/ahmedabad/v2",
  "complaint": "…",
  "insurer_position": "…",
  "findings": "…",
  "award": "…"
}
```

### `labelled/<doc_id>.json`

Same fields as the processed record (§4) except `split` and `dataset_version`, plus `outcome_rule` (which mapping rule produced the label). Written only after the anonymiser runs.

---

## 4. Processed record — `data/processed/v<hash>/{train,val,test}.parquet` `[PR 7]`

One row per usable decision. This is the only dataset that may be published (if PR 2 terms allow).

| Field | Arrow type | Nullable | Description |
|---|---|---|---|
| `doc_id` | `string` | no | Joins to the manifest **locally only** |
| `source` | `dictionary<string>` | no | `Source` |
| `country` | `dictionary<string>` | no | `Country` |
| `decision_date` | `date32` | no | Drives the split |
| `decision_year` | `int16` | no | For breakdowns |
| `split` | `dictionary<string>` | no | `Split` |
| `insurer_type` | `dictionary<string>` | no | `InsurerType` |
| `product` | `dictionary<string>` | no | `Product` |
| `rejection_reason` | `dictionary<string>` | no | `RejectionReason` |
| `claim_amount_band` | `dictionary<string>` | no | `ClaimAmountBand` (`unknown` if not stated) |
| `facts_text` | `large_string` | no | Anonymised complaint + insurer position. **Model input** |
| `findings_text` | `large_string` | no | Anonymised findings. **Explainer only** |
| `label` | `dictionary<string>` | no | `Label` |
| `label_binary` | `bool` | no | True for `upheld` / `partially_upheld` |
| `facts_chars` | `int32` | no | Length, for EDA and filtering |
| `lexicon_hits` | `int16` | no | Outcome-word count in `facts_text` (leakage metric L2) |
| `dataset_version` | `string` | no | Content hash of the build |

**Not present by design:** `url`, award text, any personal identifier.

> Insurer names are public parties and survive anonymisation inside the text (`../04-data-sources.md` §5), but the processed schema in `../05-project-description.md` §6.3 stores only `insurer_type` as a column. Adding an `insurer_name` column would change the dataset hash, so it needs a new dataset version.

### File layout

```text
data/processed/
├── LATEST                       # contains "v3f9a1c2e"
└── v3f9a1c2e/
    ├── train.parquet            # decision_date ≤ 2023-12-31
    ├── val.parquet              # 2024
    ├── test.parquet             # ≥ 2025-01-01
    ├── DATA_CARD.md
    ├── funnel.csv               # stage counts (see data-flow.md §3)
    └── schema.json              # Arrow schema dump, checked in tests
```

- Compression: `zstd`. Row order: `decision_date`, then `doc_id` — required for a stable content hash.
- `dataset_version` = first 8 hex chars of SHA-256 over the concatenated, sorted, canonical-JSON records of all three splits.
- Loading:

```python
import pyarrow.parquet as pq
train = pq.read_table("data/processed/v3f9a1c2e/train.parquet").to_pandas()
```

### Validation (run in `tests/test_schema.py`)

- Arrow schema equals `schema.json`.
- Every enum column contains only listed values.
- `split` agrees with `decision_date` (see `leakage-contract.md` §4, L3).
- `label_binary == (label != "rejected")`.
- No value in `facts_text` or `findings_text` matches the phone, PIN-code, email or policy-number patterns (NFR-02b).

---

## 5. Precedent index entry — `index/precedents/` `[PR 13]`

One entry per processed record (FR-13a). Backend: ChromaDB or FAISS + a sidecar Parquet for metadata.

| Field | Type | Use |
|---|---|---|
| `id` | string | = `doc_id` |
| `embedding` | float32[d] | Embedding of `facts_text` (model name and `d` in `config.yaml`) |
| `document` | string | `findings_text`: the only text the explainer reads |
| `source`, `country` | string | Shown with each precedent (gap G1) |
| `decision_date` | int (`YYYYMMDD`) | Date filter; stored as int so range filters work in ChromaDB |
| `label` | string | Shown and used for outcome-agreement evaluation |
| `rejection_reason`, `insurer_type`, `decision_year` | string / int | Precedent Explorer filters |
| `dataset_version` | string | Index must match the loaded dataset version |

```text
index/precedents/
├── chroma/                 # or faiss.index
├── metadata.parquet        # same fields as above, minus embedding
└── index_meta.json         # embedding model, dimension, dataset_version, built_at
```

At startup the pipeline refuses to run if `index_meta.json.dataset_version` differs from `data/processed/LATEST`.

---

## 6. Model artefacts — `models/` `[PR 9–12]`

| Path | Contents |
|---|---|
| `models/baselines/<name>.joblib` | Fitted baseline + `meta.json` (run ID, dataset version) |
| `models/lora-adapter/` | `adapter_config.json`, `adapter_model.safetensors`, `meta.json` (base model ID, seed, dataset version, run ID) |
| `models/calibrator.pkl` | Fitted calibrator + method (`temperature` / `isotonic`) |
| `models/thresholds.json` | Abstain confidence threshold and the val coverage/accuracy it was chosen at |

Base-model weights are never committed; `meta.json` names the Hugging Face model ID to download.
