# ClaimSense — v2 Backlog

> Ideas parked by the scope-creep rule (risk **R15**): **a feature not in the 18 PRs goes here, not into v1.** Nothing on this list is worked on before v1.0 is tagged.

**Author:** Diya Shrivastava · **Source:** `scope.md` §3.2, §4 and §6 · **Rule owner:** `planning/risk-register.md` R15

---

## 1. Intake rules

1. Any new idea raised during the build is written here as a row, with its **origin** (user story, gap, doc section, PR, or "product idea").
2. It stays **Parked** until v1.0 is tagged.
3. It can move into v1 only if it **replaces** an equal or larger piece of planned work and `planning/pr-plan.md` is updated in the same change.
4. Anything touching **legal advice, agents or MCP** needs an explicit scope decision recorded in `scope.md` §6. It is never a quiet addition.
5. When an idea is raised inside a PR, the PR description links the backlog row instead of implementing it.

---

## 2. Status legend

| Status | Meaning |
|---|---|
| **Parked** | Logged; not to be worked on before v1.0 |
| **Needs scope review** | Excluded from v1 by design; needs its own scope decision before planning |
| **Ready** | Post-v1.0; prerequisite met; can be planned into v2 |
| **Planned** | Assigned to a v2 PR |
| **Dropped** | Rejected after review; reason recorded |

---

## 3. Backlog

| ID | Item | Category | Origin | Prerequisite | Status |
|---|---|---|---|---|---|
| V2-01 | Show "chance of any payment" (binary view) on the Predict page | Product | User story US-P9, gap G2 | Calibrate the binary head separately | Parked |
| V2-02 | Name the IRDAI standard exclusion (Excl01–Excl18) a precedent turned on | Explainability | US-A7, gap G3; `04-data-sources.md` §6 | Exclusion-tagging rules + hand-checked sample | Parked |
| V2-03 | Link precedents to clauses in insurer Customer Information Sheets | Explainability | `04-data-sources.md` §6 | CIS collection and terms check | Parked |
| V2-04 | Hindi and regional-language input | Coverage | `scope.md` §3.2 | Translated evaluation set | Parked |
| V2-05 | Other insurance lines (motor, life, travel) | Coverage | `scope.md` §3.2 | New sources, labels and splits | Parked |
| V2-06 | Additional ombudsmen or regulators | Data | `scope.md` §3.2 | Terms-of-use audit per source | Parked |
| V2-07 | Policy / rejection-letter upload with fact extraction | Product | `scope.md` §3.2 | PII handling for user documents | Parked |
| V2-08 | Hosted deployment with an HTTP API around `predict()` | Platform | `scope.md` §3.2 | Rate limiting, logging policy, no storage of user facts by default | Parked |
| V2-09 | Scheduled dataset refresh with new decisions | Data | `scope.md` §3.2 | Versioned re-split, drift report | Parked |
| V2-10 | User feedback on predictions (helpful / not helpful) | Product | Product idea | Consent and storage policy | Parked |
| V2-11 | MCP server exposing precedent search | Platform | Out-of-scope list (`scope.md` §3.1) | v1 stable; separate scope review | Needs scope review |
| V2-12 | Agentic case-preparation assistant | Product | Out-of-scope list (`scope.md` §3.1) | Must stay clear of legal advice; separate scope review | Needs scope review |

V2-11 and V2-12 are listed only so the ideas are not lost. They are excluded from v1 **by design** (decision D9 and the no-MCP rule) and need their own scope decision before they can be planned.

---

## 4. Constraint-driven exclusions (not backlog items)

These v1 limits are recorded in `scope.md` §3.2 but are not standalone features. They are noted here so they are not re-raised as new ideas:

| Constraint | Why it stays | Revisit when |
|---|---|---|
| Full fine-tuning or paid GPU / API inference | NFR-07: free resources only | Budget or compute changes |
| Live re-scraping inside v1 | Dataset frozen per version for reproducibility | Covered by V2-09 |
| User accounts and saved history | Storing user claims raises privacy obligations | Covered by V2-08 / V2-10 prerequisites |

---

## 5. Permanently out (never backlog)

| Item | Reason |
|---|---|
| Legal advice; drafting complaints, appeals or legal arguments | R12; ClaimSense describes how similar cases went, it does not advise |
| Findings as model input | D1; leaks the answer |
| Random train/test split | D2; overstates accuracy |
| Free-form (ungrounded) LLM explanations | D6, R10; invented reasons |
| Publishing raw PDFs or un-anonymised text | D10; decisions name real complainants |

---

## 6. Intake log

New rows raised during the build are logged here first, then added to §3.

| Date | Raised in (PR / doc) | Idea | Assigned ID | Decision |
|---|---|---|---|---|
| — | `scope.md` §4 | V2-01 to V2-12 | V2-01–V2-12 | Parked at backlog creation |
