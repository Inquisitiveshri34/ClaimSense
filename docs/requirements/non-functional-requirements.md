# ClaimSense — Non-Functional Requirements

> How well the system must behave. Twelve requirements covering safety of the data and model, trustworthiness of the output, and engineering quality — each with a measure, the PR that first enforces it, and how it is verified.

**Author:** Diya Shrivastava

**Source:** `05-project-description.md` §5. Testable checks for each requirement: `acceptance-criteria.md`.

---

## 1. Requirements

| ID | Category | Requirement | Measure |
|---|---|---|---|
| **NFR-01** | Leakage safety | No findings or award text in model input | Leak-probe tests pass in CI |
| **NFR-02** | Privacy | No personal identifiers in processed data | 0 hits on a 100-document manual sample + automated pattern scan |
| **NFR-03** | Calibration | Probabilities match observed frequencies | Test ECE ≤ 0.05 |
| **NFR-04** | Faithfulness | Explanations supported by cited precedents | 100% after filter; manual audit agrees ≥ 90% |
| **NFR-05** | Reproducibility | Results can be regenerated from a fresh clone | Pinned dependencies, fixed seeds, dataset hash, one-command pipeline |
| **NFR-06** | Latency | Interactive response | ≤ 10 s per prediction on a laptop CPU (excluding first model load) |
| **NFR-07** | Cost | Runs on free resources | Training on free Kaggle/Colab GPU; inference without paid GPU |
| **NFR-08** | Responsible scraping | Sources are not overloaded | ≤ 1 request per 2–3 s, single-threaded, identified User-Agent |
| **NFR-09** | Licensing | Only permitted data is published | PR 2 checklist complete per source |
| **NFR-10** | Code quality | Maintainable and tested | ruff + black clean; unit and pipeline tests pass in CI |
| **NFR-11** | Transparency | Users can see limits | Model card lists metrics, failure modes and abstain rate |
| **NFR-12** | Usability | Understandable by a non-expert | Outcome, probability and explanation readable without jargon |

---

## 2. Detail by group

### 2.1 Data and model safety

| ID | Why it matters | Enforced from | Verified by | Related risk |
|---|---|---|---|---|
| NFR-01 | If findings leak into input, accuracy measures reading the answer, not prediction | PR 6 (then every PR via CI) | Leak-probe tests; outcome-word lexicon check; facts-only vs findings-included gap in PR 14 | R3 |
| NFR-02 | Indian awards name complainants and give addresses | PR 6 | Manual 100-doc sample + full automated regex scan | R5 |
| NFR-08 | Public ombudsman sites are not built for bulk traffic | PR 3, PR 4 | Collector tests on rate limit, concurrency and User-Agent | — |
| NFR-09 | Redistribution rights differ per source | PR 2 | Terms-of-use checklist (`04-data-sources.md` §2) | R2 |

**Default if terms are unclear (NFR-09):** collect for local research use only; publish code, aggregate statistics and model weights; do **not** publish the processed text dataset.

### 2.2 Output trustworthiness

| ID | Why it matters | Enforced from | Verified by | Related risk |
|---|---|---|---|---|
| NFR-03 | Users act on the number, so 70% must mean 70% | PR 12 | ECE, Brier score and reliability diagram on the test split | — |
| NFR-04 | An explanation with invented reasons is worse than none | PR 13 (filter), PR 15 (audit) | Automated citation coverage; 40-case hand-labelled audit | R10 |
| NFR-11 | Users must see where the model is weak | PR 17, PR 18 | Model card sections + Model Card page | R12, R13 |
| NFR-12 | Primary users are non-experts in a stressful situation | PR 17 | Plain-language review of sample outputs | R12 |

### 2.3 Engineering

| ID | Why it matters | Enforced from | Verified by | Related risk |
|---|---|---|---|---|
| NFR-05 | Portfolio claim: "a fresh clone reproduces the reported metrics" | PR 1 (pinning, seeds), PR 7 (hash), PR 18 (fresh-clone run) | Fresh-clone reproduction in a clean environment | — |
| NFR-06 | The app must feel interactive | PR 16 | CPU latency benchmark | — |
| NFR-07 | Solo student project with no budget | PR 11 (training), PR 16 (inference) | Training on free GPU; inference test with GPU hidden | R9, R11 |
| NFR-10 | 18 PRs by one person need guard-rails | PR 1 (then every PR) | CI: ruff, black, pytest | — |

---

## 3. Traceability — NFR to PR

| PR | Introduces or verifies |
|---|---|
| 1 | NFR-05 (pinning, seeds), NFR-10 (CI) |
| 2 | NFR-09 |
| 3, 4 | NFR-08 |
| 6 | NFR-01, NFR-02 |
| 7 | NFR-05 (dataset hash) |
| 11 | NFR-07 (free-GPU training) |
| 12 | NFR-03 |
| 13 | NFR-04 (automated filter) |
| 14 | NFR-01 (facts vs findings gap), NFR-05 (one-command report) |
| 15 | NFR-04 (manual audit) |
| 16 | NFR-06, NFR-07 (CPU inference) |
| 17 | NFR-11 (Model Card page), NFR-12 |
| 18 | NFR-05 (fresh-clone reproduction), NFR-11 (`MODEL_CARD.md`) |

NFR-01 and NFR-10 are **continuous**: once introduced, their checks run on every later PR.

---

## 4. Quality gates (summary)

| Gate | Condition | Blocks |
|---|---|---|
| CI | ruff, black, unit tests, leak-probe tests green | Any merge |
| Data | Segmenter ≥ 95% on 50 hand-checked docs; 0 PII hits on 100-doc sample | Dataset v1 freeze (PR 7) |
| Model | Fine-tuned model beats every baseline on validation; test ECE ≤ 0.05 | PR 11, PR 12 merge |
| Release | Fresh clone reproduces reported test metrics with one command | v1.0 tag (PR 18) |
