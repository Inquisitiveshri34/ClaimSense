# ClaimSense — Scope

> What v1.0 includes, what it deliberately leaves out, and where new ideas go. The rule (risk R15): **a feature not in the 18 PRs goes to the v2 backlog, not into v1.**

**Author:** Diya Shrivastava

---

## 1. Scope statement

ClaimSense v1.0 is a **fixed GenAI pipeline** that predicts the likely ombudsman outcome of a **rejected health-insurance claim**, with a calibrated probability, earlier precedents and a citation-checked explanation, delivered through a local **Streamlit** app. It is built solo in **18 PRs** on free compute, from public decisions published by **CIOINS (India)**, **FOS (UK)** and **FSPO (Ireland)**.

---

## 2. In scope (v1.0)

### 2.1 Data

| Item | Detail | PR |
|---|---|---|
| Collection from three ombudsmen | CIOINS health awards, FOS insurance decisions filtered to health, FSPO health decisions | 3, 4 |
| Manifest and resumable download | Shared schema, SHA-256 hashes, polite rate limit | 3, 4 |
| PDF parsing with OCR fallback | pdfplumber + Tesseract | 5 |
| Section segmentation | Facts / insurer position / findings / award | 5 |
| 3-class labels + binary view | *Upheld / Partially upheld / Rejected*; "any payment" for evaluation | 6 |
| PII anonymisation | Presidio + Indian patterns, before any processed write | 6 |
| Dedup and temporal split | MinHash; train ≤ 2023, val 2024, test 2025+ | 7 |
| Data card | Sources, counts, anonymisation, gaps | 7 |

### 2.2 Modelling and inference

| Item | Detail | PR |
|---|---|---|
| Five baselines | Majority, rules, TF-IDF + LR, embeddings + LR, zero-shot LLM | 9, 10 |
| LoRA fine-tune | Small open model or encoder, free GPU, tracked runs | 11 |
| Calibration | Temperature scaling / isotonic; ECE ≤ 0.05 | 12 |
| Dated precedent retrieval | Vector index, earlier-only filter | 13 |
| Cited explanations | Grounded in retrieved findings, NLI citation filter | 13 |
| Abstention | Low confidence or off-topic input | 16 |
| `predict(facts)` API | Python package function | 16 |

### 2.3 Evaluation and product

| Item | Detail | PR |
|---|---|---|
| One-command evaluation report | CIs, breakdowns, India-only, facts-vs-findings gap, cross-country | 14 |
| Error analysis and fairness | 50 misclassified cases, insurer type, claim size, 40-case faithfulness audit | 15 |
| Streamlit app (local) | Predict, Precedent Explorer, Model Card, Data Explorer; disclaimer on every page | 17 |
| Docs and release | README, model card, data card, limitations, reproduction steps, v1.0 tag | 18 |

### 2.4 Supported inputs

- **Language:** English free text.
- **Insurance line:** health insurance only (individual, family floater, group and overseas mediclaim, private health).
- **Dispute type:** a claim that was rejected or partly paid, described as facts plus the insurer's stated reason.

---

## 3. Out of scope (v1.0)

### 3.1 Excluded by design

| Item | Why it is out | Design link |
|---|---|---|
| **Agents / agentic workflows** | A fixed pipeline is deterministic, testable and measurable at every step | D9 |
| **MCP servers or tools** | Adds integration surface with no gain for the core question | Overview "Not in scope" |
| **Legal advice** | ClaimSense describes how similar cases went; it does not tell anyone what to do. No drafting of complaints, appeals or legal arguments | R12, FR-19 |
| **Findings as model input** | Would leak the answer and make accuracy meaningless | D1 |
| **Random train/test split** | Overstates accuracy for future disputes | D2 |
| **Free-form (ungrounded) LLM explanations** | Risk of invented reasons | D6, R10 |
| **Publishing raw PDFs or un-anonymised text** | Decisions name real complainants | D10 |

### 3.2 Excluded by constraint (candidates for later)

| Item | Why it is out of v1 |
|---|---|
| Insurance lines other than health (motor, life, travel, home) | Different policy logic; dilutes the dataset |
| Non-English input (Hindi and regional languages) | No labelled data or evaluation set in v1 |
| Uploading policy documents or rejection letters | Needs document parsing of user files and extra privacy handling |
| Hosted public deployment, user accounts, saved history | v1 runs locally; storing user claims raises privacy obligations |
| Live or scheduled re-scraping | Dataset is frozen per version for reproducibility |
| Full fine-tuning or paid GPU/API inference | NFR-07: free resources only |
| Ombudsmen beyond CIOINS, FOS and FSPO | Fixed by PR 2–4 audit scope |

---

## 4. v2 backlog

New ideas land here first. An item enters a future plan only after v1.0 is tagged.

| ID | Item | Origin | Prerequisite |
|---|---|---|---|
| V2-01 | Show "chance of any payment" (binary view) in the Predict page | User story US-P9, gap G2 | Calibrate the binary head separately |
| V2-02 | Name the IRDAI standard exclusion (Excl01–Excl18) a precedent turned on | US-A7, gap G3; `04-data-sources.md` §6 | Exclusion-tagging rules + hand-checked sample |
| V2-03 | Link precedents to clauses in insurer Customer Information Sheets | `04-data-sources.md` §6 | CIS collection and terms check |
| V2-04 | Hindi and regional-language input | §3.2 | Translated evaluation set |
| V2-05 | Other insurance lines (motor, life, travel) | §3.2 | New sources, labels and splits |
| V2-06 | Additional ombudsmen or regulators | §3.2 | Terms-of-use audit per source |
| V2-07 | Policy / rejection-letter upload with fact extraction | §3.2 | PII handling for user documents |
| V2-08 | Hosted deployment with an HTTP API around `predict()` | §3.2 | Rate limiting, logging policy, no storage of user facts by default |
| V2-09 | Scheduled dataset refresh with new decisions | §3.2 | Versioned re-split, drift report |
| V2-10 | User feedback on predictions (helpful / not helpful) | Product idea | Consent and storage policy |
| V2-11 | MCP server exposing precedent search | Out-of-scope list | v1 stable; separate scope review |
| V2-12 | Agentic case-preparation assistant | Out-of-scope list | Must stay clear of legal advice; separate scope review |

V2-11 and V2-12 are listed only so the ideas are not lost; they are excluded from v1 by design and need their own scope decision.

---

## 5. Contingency scope

| Trigger | Scope change |
|---|---|
| < ~800 usable Indian health awards after PR 3 / PR 5 (R1) | Train on UK + Ireland; India becomes an out-of-distribution test set only |
| Terms forbid redistribution for a source (R2) | Publish code, aggregate statistics and model weights only; no processed text |
| Fine-tuned model does not beat baselines (R8) | Report it honestly, analyse why, ship the strongest model |
| Free-GPU limits block training (R9) | Smaller model or encoder, gradient accumulation, frequent checkpoints |

---

## 6. Change control

1. A new idea is written as a row in §4 with its origin.
2. It moves into v1 only if it **replaces** an equal or larger piece of planned work and the PR plan is updated.
3. Anything touching legal advice, agents or MCP needs an explicit scope decision recorded here, not a quiet addition.
