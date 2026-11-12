# ClaimSense — Acceptance Criteria

> Every functional and non-functional requirement turned into a **testable check**, with the **test type** and the **owning PR**. A requirement is accepted only when all its checks pass — in CI for automated checks, or recorded in the PR description for manual ones.

**Author:** Diya Shrivastava

---

## 1. Conventions

| Test type | Meaning | Where it runs |
|---|---|---|
| **Unit** | Single function on fixtures | `tests/`, CI on every PR |
| **Integration** | Several stages on saved sample data | `tests/`, CI on every PR |
| **Leak-probe** | Proves no answer text reaches model input | `tests/`, CI on every PR |
| **Metric** | Threshold on a logged evaluation metric | Experiment tracker + evaluation report |
| **Manual** | Hand check on a fixed sample; result recorded in the PR | PR description |

- Collector tests run against **saved sample pages**, never live sites (risk R14).
- Thresholds (k, confidence threshold, near-duplicate similarity) live in `config.yaml`, so tests read the same values the pipeline uses.
- **Owning PR** is the PR whose *Done when* includes the check. Continuous checks keep running on all later PRs.

---

## 2. Functional requirements

### 2.1 Data (FR-01 – FR-09)

| ID | Acceptance check | Type | Owning PR |
|---|---|---|---|
| **FR-01** | (a) Each collector, run on saved sample pages, writes files to `data/raw/<source>/`. (b) Every manifest row has `product` in the health enum (`individual_mediclaim`, `group_mediclaim`, `overseas_mediclaim`, `private_health`). (c) A real run yields > 0 documents per source, with counts recorded in the PR. | Integration + Manual | 3, 4 |
| **FR-02** | (a) Manifest schema test: every required field non-null; `decision_date` parses as ISO date; `source` ∈ {`cioins`, `fos`, `fspo`}. (b) For every row, recomputed SHA-256 of the file equals `file_sha256`. (c) All three manifests validate against **one** shared schema. | Unit + Integration | 3, 4 |
| **FR-03** | (a) Running a collector twice: the second run downloads **0** files and the manifest row count is unchanged. (b) Interrupting a run, then re-running, completes with no duplicate `doc_id` or hash and no gaps. | Integration | 3 (pattern), 4 |
| **FR-04** | (a) A text-layer PDF fixture returns non-empty text without OCR. (b) A scanned PDF fixture triggers the Tesseract path and returns non-empty text. (c) Files failing both paths are logged with a count, never silently dropped. | Unit | 5 |
| **FR-05** | (a) On 50 hand-checked documents across all sources and several Indian offices, section boundaries are correct for **≥ 95%**. (b) Every retained document has non-empty facts and award sections; others are dropped with a logged reason. | Manual + Unit | 5 |
| **FR-06** | (a) Wording fixtures for each source map to the expected label (mapping table in `04-data-sources.md` §4). (b) "Non-entertainable", "withdrawn" and "settled before award" fixtures are **excluded**. (c) Unmapped wording raises a logged entry, never a default label. (d) Hand audit of 100 labels shows **≥ 95%** accuracy (risk R6). (e) `label_binary` is true for Upheld and Partially upheld, false for Rejected. | Unit + Manual | 6 |
| **FR-07** | (a) Unit tests for each replacement: names → `[PERSON]`, addresses/PIN codes → `[ADDRESS]`, phone/email → `[CONTACT]`, policy/claim/award numbers → `[REF]`, DOB/exact ages → age band, hospitals/doctors → `[PROVIDER]`. (b) Insurer names, conditions and claim amounts survive scrubbing. (c) Pipeline-order test: nothing is written to `data/processed/` before the scrubber runs. | Unit + Integration | 6 |
| **FR-08** | (a) A fixture with a known near-duplicate pair keeps exactly one. (b) After the split, no train/validation/test pair exceeds the configured MinHash similarity threshold. | Unit + Integration | 7 |
| **FR-09** | (a) All train `decision_date` ≤ 2023-12-31; all validation in 2024; all test ≥ 2025-01-01. (b) `dataset_version` is a content hash, and rebuilding from the same inputs yields the same hash. (c) `DATA_CARD.md` lists sources, date range, counts per source and class, anonymisation method and known gaps. | Unit + Integration | 7 |

### 2.2 Modelling (FR-10 – FR-13)

| ID | Acceptance check | Type | Owning PR |
|---|---|---|---|
| **FR-10** | Five baselines — majority class, rejection-reason rules, TF-IDF + LR, embeddings + LR, zero-shot LLM — each have a tracked run with **macro-F1** and **PR-AUC** on validation. Run IDs are listed in the PR. PR 10 either beats TF-IDF or explains the gap. | Metric | 9, 10 |
| **FR-11** | (a) Each LoRA run logs config, seed, dataset version and metrics to MLflow/W&B. (b) Adapter weights exist in `models/lora-adapter/` (no base-model weights committed). (c) Validation macro-F1 is **higher than every baseline**. | Metric + Unit | 11 |
| **FR-12** | (a) Calibrator is fitted on validation indices only; a test asserts no test indices are used. (b) Reliability diagram saved to `reports/`. (c) ECE and Brier score logged before and after calibration. | Unit + Metric | 12 |
| **FR-13** | (a) Index record count equals the processed dataset count. (b) Every index record carries `decision_date`, `source`, `label` and `rejection_reason` metadata. | Integration | 13 |

### 2.3 Inference and app (FR-14 – FR-20)

| ID | Acceptance check | Type | Owning PR |
|---|---|---|---|
| **FR-14** | On fixture inputs, `predict(facts)` returns: `label` ∈ {`upheld`, `partially_upheld`, `rejected`}; `probability` ∈ [0, 1]; `precedents` of length k; `explanation` as a list of cited sentences; `abstain` as bool. Schema test passes. | Integration | 16 |
| **FR-15** | (a) For a query dated D, every returned precedent has `decision_date` < D. (b) A live query (no date) uses today. (c) Property test over random query dates finds no violation. | Unit | 13 |
| **FR-16** | (a) After filtering, every explanation sentence cites ≥ 1 precedent ID present in the retrieved set. (b) An injected unsupported sentence is removed by the NLI checker. (c) An explanation with no supported sentences returns an empty explanation, not uncited text. | Unit + Integration | 13 |
| **FR-17** | (a) Inputs below the calibrated confidence threshold return `abstain = true` and the UI hides label and probability. (b) An off-topic fixture set (e.g. motor claim, recipe, general question) returns `abstain = true`. (c) Abstain rate on the test set is reported. | Integration + Metric | 16 |
| **FR-18** | The app starts with one command, and Predict, Precedent Explorer, Model Card and Data Explorer each render without error (Streamlit `AppTest`). Precedent Explorer filters by reason, insurer type and year. | Integration | 17 |
| **FR-19** | An `AppTest` check on each of the four pages finds the disclaimer text. | Integration | 17 |
| **FR-20** | One command (e.g. `make report`) regenerates `reports/` from the frozen dataset and saved models, including bootstrap CIs, breakdowns, India-only results, facts-vs-findings gap and cross-country results. | Integration | 14 |

---

## 3. Non-functional requirements

| ID | Acceptance check | Type | Owning PR |
|---|---|---|---|
| **NFR-01** | (a) Leak-probe: no sentence or long n-gram from a document's findings or award appears in its `facts_text`. (b) Outcome-word lexicon rate in `facts_text` is measured and reported. (c) Facts-only vs findings-included accuracy gap is reported in the evaluation report. All leak-probe tests run in CI on every PR. | Leak-probe + Metric | 6 (continuous); gap in 14 |
| **NFR-02** | (a) Manual review of 100 randomly sampled processed documents finds **0** PII hits. (b) Automated scan of the full processed set finds **0** matches for phone, PIN-code or policy-number patterns. | Manual + Integration | 6 |
| **NFR-03** | ECE on the **test** split ≤ **0.05** (binning scheme fixed in `config.yaml`); Brier score and reliability diagram reported. | Metric | 12 |
| **NFR-04** | (a) Automated: 100% of displayed explanation sentences are supported by a cited precedent. (b) Manual audit of 40 hand-labelled cases agrees with the checker on **≥ 90%** of sentences. | Metric + Manual | 13 (a), 15 (b) |
| **NFR-05** | (a) Dependencies pinned in a lock file; seeds set in `config.yaml`. (b) In a clean environment, a fresh clone runs the one-command pipeline, the dataset hash matches, and test metrics are reproduced (identical for deterministic steps; within the reported bootstrap CI for GPU training). | Integration + Manual | 1, 7, 18 |
| **NFR-06** | Benchmark of 20 fixture queries on a laptop CPU after warm-up: every query ≤ **10 s**; median and max reported. | Metric | 16 |
| **NFR-07** | (a) The fine-tuning notebook completes on a free Kaggle/Colab GPU, with checkpointing. (b) The inference test passes with no GPU visible (`CUDA_VISIBLE_DEVICES=""`). | Manual + Integration | 11, 16 |
| **NFR-08** | Collector tests with a mocked clock: interval between requests ≥ 2 s; one worker only; User-Agent contains the project name and a contact email. | Unit | 3, 4 |
| **NFR-09** | (a) For each source, all five boxes in `04-data-sources.md` §2 are ticked before that source's collector merges. (b) `data/processed/` is published only if the redistribution box is ticked for every source in it; otherwise the default (code, stats, weights only) applies. (c) `data/raw/` is git-ignored. | Manual | 2 |
| **NFR-10** | CI runs `ruff`, `black --check` and `pytest` on every PR; all pass before merge. | Integration | 1 (continuous) |
| **NFR-11** | (a) `MODEL_CARD.md` has sections for metrics with CIs, calibration, failure modes (from PR 15) and abstain rate. (b) The Model Card page shows the same content. | Manual + Integration | 17, 18 |
| **NFR-12** | Ten sample outputs reviewed against a plain-language checklist: outcome stated in one sentence; probability phrased in words (e.g. "about 7 in 10 similar cases"); any term from a jargon list (repudiation, non-disclosure, waiting period, exclusion) followed by a short gloss. | Manual | 17 |

---

## 4. Checks per PR (merge checklist)

| PR | Must pass |
|---|---|
| 1 | NFR-10 CI green; NFR-05(a) deps pinned, seeds set |
| 2 | NFR-09 checklist complete per source |
| 3 | FR-01–03 (CIOINS); NFR-08 |
| 4 | FR-01–03 (FOS, FSPO); FR-02(c) one schema; NFR-08 |
| 5 | FR-04, FR-05 |
| 6 | FR-06, FR-07; NFR-01 leak probes; NFR-02 |
| 7 | FR-08, FR-09; NFR-05 dataset hash |
| 8 | Notebook renders end to end; findings written |
| 9 | FR-10 (three baselines) |
| 10 | FR-10 (two baselines) |
| 11 | FR-11; NFR-07(a) |
| 12 | FR-12; NFR-03 |
| 13 | FR-13, FR-15, FR-16; NFR-04(a) |
| 14 | FR-20; NFR-01(c) gap reported |
| 15 | NFR-04(b); failure modes written up with counts |
| 16 | FR-14, FR-17; NFR-06; NFR-07(b) |
| 17 | FR-18, FR-19; NFR-11(b); NFR-12 |
| 18 | NFR-05(b) fresh-clone reproduction; NFR-11(a) |

---

## 5. Global Definition of Done

A PR is done when:

1. Its rows in §4 pass.
2. CI is green (NFR-10) and leak probes still pass (NFR-01).
3. Manual check results, metric values and run IDs are pasted into the PR description.
4. Any new risk or gap is added to `scope.md` (v2 backlog) or `05-project-description.md` §10.
