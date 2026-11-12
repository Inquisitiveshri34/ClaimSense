# ClaimSense — Retrieval Design

> How ClaimSense finds the past decisions most similar to a user's dispute: what is embedded, with which model, how many precedents are returned, how the date filter blocks precedents from the future, and how the index is built, versioned and evaluated.

**Author:** Diya Shrivastava · **Owning PR:** 13 · **Status:** Planned

**Related:** FR-13, FR-15, design decision D7, `../architecture/leakage-contract.md` (L5), `../architecture/data-schema.md` §5, `../architecture/pipeline-interface.md` §3–§6, `prompt-spec.md` §5, `../data/manual-audit-protocol.md` (A5).

---

## 1. What retrieval is for

1. **Show precedents** to the user: the most similar earlier decisions, with country, year, outcome and an excerpt of the findings.
2. **Ground the explanation:** the explainer reads only these precedents' findings (D6).
3. **Gate the answer:** too few similar cases → `NO_PRECEDENTS` abstain.

Retrieval does **not** feed the classifier. The prediction comes from the fine-tuned model; precedents are evidence shown beside it.

---

## 2. What is embedded

| Side | Text | Why |
|---|---|---|
| **Query** | The user's facts (or a test record's `facts_text` offline) | That is all a user has |
| **Index key** | Each precedent's `facts_text` | Facts are compared with facts, so "similar case" means similar situation, not similar wording of a verdict |
| **Index payload** | Each precedent's `findings_text` + metadata | What the explainer and the user see |

Embedding findings instead of facts was rejected: findings are written in the ombudsman's voice, so a user's description would match them poorly.

---

## 3. Embedding model

### Choice

| Rank | Model | Dim | Max tokens | Licence | Note |
|---|---|---|---|---|---|
| **1** | `BAAI/bge-small-en-v1.5` | 384 | 512 | MIT | **Default.** Small and fast on CPU; same encoder as baseline B4 |
| 2 | `BAAI/bge-base-en-v1.5` | 768 | 512 | MIT | Tried if topic match is weak; ~3× slower |
| 3 | `sentence-transformers/all-MiniLM-L6-v2` | 384 | 256 | Apache-2.0 | Speed fallback; short window means more chunks |

Confirm sizes and licences on the model cards when PR 13 opens.

### Long text

`facts_text` is often longer than 512 tokens. Each text is split into **400-token windows with 50-token overlap**; each window is embedded and L2-normalised; the document vector is the **normalised mean** of its windows. One vector per record keeps the index at one entry per decision (`data-schema.md` §5).

### Query instruction

The bge models accept an instruction prefix for short-query → long-passage search. ClaimSense is symmetric (facts ↔ facts), so **no prefix** is used on either side. This is checked once in the encoder comparison (E-015).

### How the encoder is chosen

On val queries (each val record as a query, searching train records only), compare candidates by the automatic proxies in §7 at k = 5. Pick the best topic match@5 among models with query embedding time ≤ 0.5 s on CPU.

---

## 4. Number of precedents (k) and the similarity floor

| Key (`config.yaml`) | Start | How it is set |
|---|---|---|
| `retrieve.k` | 5 | Sweep {3, 5, 8, 10} on a val dev set: explanation sentences kept after the citation check vs prompt length and latency. Choose the smallest k within 1 point of the best kept-sentence rate |
| `retrieve.max_k` | 20 | Upper bound for the Precedent Explorer page |
| `retrieve.min_k` | 2 | Fewer than this above the floor → `NO_PRECEDENTS` |
| `retrieve.min_similarity` | 0.35 | Set to the **5th percentile** of top-1 cosine similarity over val queries, so roughly 5% of in-scope val queries would have no close precedent. Recorded with the percentile used |

Values are recorded in `models/thresholds.json` beside the abstain threshold, with the val statistics used to pick them.

---

## 5. The date filter (L5)

| Rule | Detail |
|---|---|
| Required argument | `search(query_vec, before: date, k, exclude_doc_id=None)`; there is no default for `before` and no unfiltered search method |
| Comparison | Strictly earlier: `decision_date < before` |
| Live use | `before` = today |
| Offline evaluation | `before` = the query record's own `decision_date`; the query record is excluded by `doc_id` |
| Storage | `decision_date` stored as an integer `YYYYMMDD` so range filters are exact |

### Decision: earlier test-split records may be precedents

For a test query dated June 2025, a test record dated February 2025 is a legitimate precedent: it really was published before the query. This matches live use, where every earlier decision is available. It is **not** a training leak, because the classifier never saw it; it only appears as retrieved evidence. The evaluation report states this rule.

### Near-duplicates

Dedup before splitting (L4) already keeps only the earliest copy of each case, so the same dispute cannot appear as its own precedent under another ID.

---

## 6. Ranking

- **v1:** pure cosine similarity, exact search, top-k after the date filter.
- **Not in v1** (v2 backlog): boosting same-country precedents, MMR diversity re-ranking, cross-encoder re-ranking. Each is easy to add but changes what "most similar" means, so it needs its own evaluation.
- **Country mix is reported** instead: the share of Indian precedents for Indian queries (risk R13). The app always shows each precedent's country.

---

## 7. Index build

### Backend

**Exact search with FAISS `IndexFlatIP`** on normalised vectors (cosine = inner product), with the date filter applied as a mask before ranking.

| Option | Why / why not |
|---|---|
| **FAISS flat (chosen)** | Exact and deterministic, so results reproduce (NFR-05); the dataset is small (thousands, not millions), so brute force is fast; no server process |
| ChromaDB | Built-in metadata filters, but approximate (HNSW) search can return slightly different neighbours across builds; kept as an alternative in `02-architecture.md` |

### Command

```bash
python -m claimsense.retrieve build --dataset LATEST
```

1. Load all three splits of the current dataset version.
2. Embed every `facts_text` (or reuse the B4 cache for the same encoder and dataset version).
3. Write `faiss.index`, `metadata.parquet`, `index_meta.json` to `index/precedents/`.
4. Self-check: 20 random records retrieve themselves at rank 1 when `before` is set after their date and `exclude_doc_id` is not used.

### `index_meta.json`

```json
{
  "encoder": "BAAI/bge-small-en-v1.5",
  "encoder_revision": "<Hub commit>",
  "dim": 384,
  "chunking": {"window": 400, "overlap": 50, "pool": "mean"},
  "n_records": 0,
  "dataset_version": "v________",
  "built_at": "<ISO datetime>",
  "code_commit": "<git sha>"
}
```

`predict()` refuses to start if `dataset_version` differs from `data/processed/LATEST` (`pipeline-interface.md` §5).

---

## 8. Evaluation

### Automatic proxies (val, PR 13)

For each val record as a query, with the date filter on:

| Metric | Definition |
|---|---|
| **Reason match@k** | Share of top-k precedents with the same `rejection_reason` as the query |
| **Outcome agreement@k** | Share of top-k precedents with the same `label` as the query |
| Precedent-vote accuracy | Majority label of the top-k vs the query's label; a diagnostic, not a model |
| Mean top-1 similarity | Distribution, used to set `min_similarity` |
| `NO_PRECEDENTS` rate | At the chosen floor |
| Country mix | Share of same-country precedents, per query country |
| Latency | Query embedding + search, median and max on CPU |

Precedent-vote accuracy close to the fine-tuned model's accuracy would mean the classifier adds little over nearest neighbours; worth a sentence in the report either way.

### Manual (A5, 40 test cases)

Per `manual-audit-protocol.md` §7: for each top-5 precedent, same rejection reason (y/n), same condition family (y/n), outcome. Reported as topic match@5 and outcome agreement@5 with the rubric committed in the repo.

### Results (filled in by PR 13)

| Encoder | Reason match@5 | Outcome agreement@5 | Vote accuracy | Query time (CPU) | Chosen |
|---|---|---|---|---|---|
| bge-small-en-v1.5 | | | | | |
| bge-base-en-v1.5 | | | | | |
| all-MiniLM-L6-v2 | | | | | |

---

## 9. Latency budget (part of NFR-06's 10 s)

| Step | Budget |
|---|---|
| Query embedding (≤ 4 windows) | ≤ 0.5 s |
| Date mask + exact search | ≤ 0.05 s |
| Metadata and excerpt lookup | ≤ 0.05 s |

---

## 10. Code and tests

```text
src/claimsense/retrieve/index.py    # build(), load(), embed()
src/claimsense/retrieve/search.py   # search(query_vec, before, k, exclude_doc_id)
index/precedents/                   # faiss.index, metadata.parquet, index_meta.json
```

| Test | Checks |
|---|---|
| `test_retrieval_dates.py` | Property test: random `before` dates; every result has `decision_date < before` (FR-15) |
| `test_search_requires_before` | Calling `search()` without `before` is a `TypeError` |
| `test_exclude_self` | The query's own `doc_id` never appears when excluded |
| `test_index_version_match` | Mismatched `dataset_version` raises `ArtifactMismatchError` |
| `test_search_deterministic` | Same query, same index → identical IDs and scores |
| `test_min_k_floor` | Fewer than `min_k` results above `min_similarity` → caller gets an empty list and abstains |
