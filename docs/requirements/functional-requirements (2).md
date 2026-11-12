# ClaimSense — Functional Requirements

> What the system shall do. Twenty requirements in three groups — **Data (FR-01–09)**, **Modelling (FR-10–13)**, **Inference and app (FR-14–20)** — each traced to the PR that delivers it and the module that owns it.

**Author:** Diya Shrivastava

**Source:** `05-project-description.md` §4. Testable checks for each requirement: `acceptance-criteria.md`.

---

## Conventions

- **"Shall"** marks a mandatory v1.0 requirement. All 20 FRs are **Must** priority.
- **PR** is the pull request that delivers the requirement (`03-pr-plan.md`).
- **Module** is the owning location in the repository layout (`02-architecture.md` §5).
- An FR is closed only when its acceptance check passes in CI or its manual check is recorded in the PR description.

---

## 1. Data

| ID | Requirement | PR | Module |
|---|---|---|---|
| **FR-01** | The system shall download health-related ombudsman decisions from CIOINS, FOS and FSPO into a local raw store. | 3, 4 | `collect/cioins.py`, `collect/fos.py`, `collect/fspo.py` → `data/raw/` |
| **FR-02** | The system shall record every downloaded document in a manifest with source, URL, date, insurer, product, raw outcome and file hash. | 3, 4 | `collect/` → `data/manifests/` |
| **FR-03** | Collectors shall resume from the manifest and skip already-downloaded files. | 3, 4 | `collect/` |
| **FR-04** | The system shall extract text from PDFs, using OCR when no text layer exists. | 5 | `parse/pdf_text.py` |
| **FR-05** | The system shall split each decision into facts, insurer position, findings and award sections. | 5 | `parse/segment.py` |
| **FR-06** | The system shall map each decision's outcome to *Upheld*, *Partially upheld* or *Rejected*, and exclude non-entertainable or withdrawn cases. | 6 | `label/outcomes.py` |
| **FR-07** | The system shall remove personal identifiers before writing processed text. | 6 | `label/anonymise.py` |
| **FR-08** | The system shall remove near-duplicate decisions before splitting. | 7 | `dataset/dedup.py` |
| **FR-09** | The system shall produce a versioned dataset with a temporal split and a data card. | 7 | `dataset/split.py`, `dataset/datacard.py` → `data/processed/` |

### Notes

- **FR-01** — "health-related" means CIOINS group/individual/overseas mediclaim awards, FOS insurance decisions keyword-filtered to medical/health, and FSPO "Health, Accident and Other" decisions (`04-data-sources.md` §1).
- **FR-02** — manifest fields and types are fixed in `05-project-description.md` §6.2. `office` is optional and India-only; every other field is required.
- **FR-05** — section markers are learned per source and per office (`04-data-sources.md` §4). Documents that cannot be segmented are dropped with a logged count, never guessed.
- **FR-06** — the outcome mapping table is in `04-data-sources.md` §4. Unmapped wording is logged and resolved by hand. A binary `label_binary` ("any payment ordered") is derived alongside the 3-class label (design decision D3).
- **FR-07** — replacement tokens: `[PERSON]`, `[ADDRESS]`, `[CONTACT]`, `[REF]`, `[PROVIDER]`, age bands. Insurer names, medical conditions and claim amounts are kept (`04-data-sources.md` §5).
- **FR-09** — split: **train ≤ 2023, validation 2024, test 2025+**, fixed at build time and rebuilt only with a new dataset version.

---

## 2. Modelling

| ID | Requirement | PR | Module |
|---|---|---|---|
| **FR-10** | The system shall train and log at least five baselines: majority class, rules, TF-IDF + LR, embeddings + LR, zero-shot LLM. | 9, 10 | `models/baselines.py` |
| **FR-11** | The system shall fine-tune a classifier with LoRA and track every run's configuration and metrics. | 11 | `models/finetune.py` → `models/lora-adapter/` |
| **FR-12** | The system shall calibrate predicted probabilities on the validation split. | 12 | `models/calibrate.py` → `models/calibrator.pkl` |
| **FR-13** | The system shall index past decisions with their dates for similarity search. | 13 | `retrieve/index.py` → `index/precedents/` |

### Notes

- **FR-10** — majority class, rules and TF-IDF + LR land in PR 9; embeddings + LR and zero-shot LLM land in PR 10. Every baseline logs macro-F1 and PR-AUC.
- **FR-11** — tracking via MLflow or Weights & Biases. Only adapter weights are saved, not the base model.
- **FR-12** — temperature scaling or isotonic regression, fitted on validation only; the test split is never used for fitting.
- **FR-13** — the index stores anonymised findings and metadata (source, country, decision date, outcome, rejection reason, insurer type) so retrieval can filter by date.

---

## 3. Inference and app

| ID | Requirement | PR | Module |
|---|---|---|---|
| **FR-14** | `predict(facts)` shall return label, calibrated probability, top-k precedents, explanation and an abstain flag. | 16 | `pipeline.py` |
| **FR-15** | Retrieval shall return only decisions dated before the query case (or before today for live queries). | 13 | `retrieve/search.py` |
| **FR-16** | Every explanation sentence shall cite a retrieved precedent; unsupported sentences shall be removed. | 13 | `explain/generate.py`, `explain/cite_check.py` |
| **FR-17** | The system shall abstain when calibrated confidence is below a set threshold or the input is not a health-insurance claim dispute. | 16 | `pipeline.py` |
| **FR-18** | The app shall provide Predict, Precedent Explorer, Model Card and Data Explorer pages. | 17 | `app/` |
| **FR-19** | Every app page shall show the not-legal-advice disclaimer. | 17 | `app/` |
| **FR-20** | One command shall regenerate the full evaluation report. | 14 | evaluation entry point → `reports/` |

### Notes

- **FR-14** — output contract is defined in `PRD.md` §5.2. When `abstain` is true, the label and probability are not shown to the user.
- **FR-16** — the explainer sees only the retrieved precedents' findings; an NLI cross-encoder checks each sentence against its cited precedent.
- **FR-17** — the confidence threshold is chosen from the coverage-vs-accuracy curve on validation and stored in `config.yaml`.
- **FR-19** — disclaimer text: *"ClaimSense describes how similar past cases were decided. It is not legal advice; the ombudsman decides each case on its own facts."*
- **FR-20** — the report covers test metrics with bootstrap CIs, breakdowns, India-only results, facts-only vs findings-included gap and cross-country generalisation (`03-pr-plan.md`, PR 14).

---

## 4. Traceability — FR to PR

| PR | Delivers |
|---|---|
| 3 | FR-01, FR-02, FR-03 (CIOINS) |
| 4 | FR-01, FR-02, FR-03 (FOS, FSPO) |
| 5 | FR-04, FR-05 |
| 6 | FR-06, FR-07 |
| 7 | FR-08, FR-09 |
| 9 | FR-10 (majority, rules, TF-IDF + LR) |
| 10 | FR-10 (embeddings + LR, zero-shot LLM) |
| 11 | FR-11 |
| 12 | FR-12 |
| 13 | FR-13, FR-15, FR-16 |
| 14 | FR-20 |
| 16 | FR-14, FR-17 |
| 17 | FR-18, FR-19 |

PRs 1, 2, 8, 15 and 18 deliver no FR directly; they serve non-functional requirements (see `non-functional-requirements.md` §3).
