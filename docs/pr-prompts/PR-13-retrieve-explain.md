# PR 13 · Precedent retrieval + cited explanations

| | |
|---|---|
| **Branch** | `feat/retrieve-explain` |
| **Depends on** | PR 12 |
| **Covers** | FR-13, FR-15, FR-16, NFR-04(a) · **Risks** R10, R11 |
| **Read first** | `docs/modelling/retrieval-design.md`, `docs/modelling/prompt-spec.md` (P-EX), `docs/modelling/citation-checking.md`, `docs/evaluation/retrieval-rubric.md`, `docs/architecture/leakage-contract.md` (precedents from the future), `docs/architecture/pipeline-interface.md` §2 (`Precedent`, `ExplanationSentence`), `docs/testing/test-fixtures.md` §6–§7 |
| **Done when** | Every explanation sentence cites a retrieved precedent; uncited or unsupported sentences are dropped |

---

## 1. Goal

Find the most similar **earlier** decisions and write an explanation grounded only in their findings, then delete any sentence a cited precedent does not support.

## 2. Files to add

| File | Contents |
|---|---|
| `src/claimsense/retrieve/index.py` | `PrecedentIndex.build(records, encoder, out_dir)`: chunk **findings** (`window_tokens`, `overlap_tokens`) of all processed records (all splits — retrieval is date-filtered, not split-filtered; follow the spec if it says otherwise); embed; FAISS inner-product index on normalised vectors; sidecar parquet with `doc_id`, `chunk_id`, `decision_date`, `source`, `country`, `label`, `rejection_reason`, `insurer_type`, `findings_excerpt`; `index_meta.json` (encoder name + revision, chunking, `dataset_version`, count) |
| `src/claimsense/retrieve/search.py` | `search(query_text, before: date, k, exclude_doc_id=None) -> list[Precedent]`: embed query (facts only), over-fetch, drop chunks with `decision_date >= before` and `doc_id == exclude_doc_id`, aggregate chunk→doc by max similarity, apply `min_similarity`, return top-k; returns fewer if fewer qualify |
| `src/claimsense/retrieve/__main__.py` | `python -m claimsense.retrieve build` (`make index`), `sweep-k` (val sweep for k), `calibrate-thresholds` (val 5th-percentile similarity → `models/thresholds.json`) |
| `src/claimsense/explain/generate.py` | `Explainer(client, prompt_id="P-EX-v1")`: prompt contains the facts + up to `excerpt_windows` findings excerpts per precedent (never awards); asks for JSON `[{text, cites}]`; ≤ `max_sentences`; malformed JSON → `[]` + warning |
| `src/claimsense/explain/cite_check.py` | `CitationChecker(nli)`: structural S1–S4 (`NO_CITE`, `UNKNOWN_CITE`, `ADVICE_PHRASE`, …) then NLI entailment of each sentence against each cited excerpt; keep if max entailment ≥ `min_entailment` else `LOW_ENTAILMENT`; returns `(kept: list[ExplanationSentence], dropped: list[(sentence, code)])`; all dropped → warning `NO_SUPPORTED_EXPLANATION` |
| `src/claimsense/explain/nli.py` | `NLIModel` protocol; `CrossEncoderNLI(model, revision)` |
| `src/claimsense/prompts/P-EX-v1.txt` | Explanation prompt; hash added to `registry.yaml` |
| `tests/stubs/stub_nli.py`, `tests/stubs/stub_explainer.py` | Read `tests/fixtures/pipeline/nli_scores.yaml` and `explainer/*.json` |
| `tests/fixtures/leak/retrieval_index.jsonl`, `tests/fixtures/models/index_tiny/`, `tests/fixtures/pipeline/explainer/*.json`, `tests/fixtures/pipeline/nli_scores.yaml` | Per `test-fixtures.md` |
| Tests | `tests/integration/test_index_build.py`, `tests/leak/test_retrieval_dates.py`, `tests/unit/test_citation_structural.py`, `tests/pipeline/test_citation_filter.py`, `tests/slow/test_nli_real_model.py` |
| `.github/workflows/slow.yml` | Manual dispatch; network allowed; HF cache keyed on pinned revisions; runs `make test-slow` |

## 3. Files to modify

`config.yaml` (`retrieve`, `explain`, `cite_check`; pin `encoder_revision`, `model_revision`), `config.py`, `models/thresholds.json` (created by `calibrate-thresholds`; committed, because `configuration.md` §4 makes it the mirror of the config values; make sure `.gitignore` allows `models/thresholds.json` while still ignoring weights), `pyproject.toml` (`faiss-cpu`), `Makefile` (`index`), `scripts/ci_guard.sh` (prompts rule now covers P-EX), `CHANGELOG.md`.

## 4. Tests to write

- **`test_index_build.py`**: toy index from `retrieval_index.jsonl` with the hashing embedder; meta fields; rebuild → identical; only findings text is indexed (no award text in sidecar).
- **`test_retrieval_dates.py`** (`leak`, Hypothesis, `derandomize=True`): for any `before` date, no result has `decision_date >= before`; same-date precedents excluded; the query document is excluded via `exclude_doc_id`; `local_data` variant on the real index.
- **`test_citation_structural.py`**: S2–S4 drops with the right codes.
- **`test_citation_filter.py`**: `supported.json` → all kept; `injected_unsupported.json` → that one sentence dropped `LOW_ENTAILMENT`; `all_unsupported.json` → `[]` + warning; `malformed.json` → `[]` + warning; every kept sentence's cites ⊆ precedent ids.
- **`test_nli_real_model.py`** (`slow`): real cross-encoder drops an injected unsupported sentence and keeps a paraphrase.

## 5. E2E tests

`stages.py`: `run_index(world)` (→ `run_build`, hashing embedder), `run_explain(world, query)` with a stub LLM that writes sentences **from the retrieved excerpts it is given** plus one invented sentence, and a stub NLI that scores by token overlap.

**`tests/e2e/test_e2e_13_retrieve_explain.py`**:
- Index built from the world dataset; `index_meta.dataset_version == LATEST`.
- For every world **test** record used as a query with `before = its decision_date` and `exclude_doc_id = its id`: all precedents are strictly earlier, never the query itself.
- Retrieval quality signal: for queries with the planted reason, ≥ half of top-5 precedents share that `rejection_reason` (proves embeddings + chunking + aggregation work together on real chain output).
- Explanation: the invented sentence is dropped; every kept sentence cites a returned precedent; the prompt sent to the stub LLM contains no award text and no findings of the query document.
- Contracts extended: index ↔ dataset versions.

## 6. Definition of done

`make pr-check` → ALL CHECKS PASSED; run `slow.yml` on the branch and paste the link; raise the floor.

## 7. Manual checks (Diya)

- [ ] `make index` on real data; `python -m claimsense.retrieve sweep-k` and `calibrate-thresholds`; commit `models/thresholds.json` + updated `config.yaml` values.
- [ ] Dev-set run on 30 val queries (real LLM + real NLI): paste % sentences kept, % queries with ≥ 1 kept sentence, retrieval rubric score.
- [ ] Spot-check 5 outputs by eye: cites valid, dates earlier.
