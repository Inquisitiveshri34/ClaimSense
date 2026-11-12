# Data sources

ClaimSense learns from **published decisions of three insurance ombudsmen**: real health-insurance disputes with real outcomes. This file is the short version. The full record of what each source holds, how it is collected, how outcomes become labels and how personal data is removed is in **[`docs/data/data-sources.md`](docs/data/data-sources.md)**.

**Owning PR:** 2 (`docs/data-sources`) · **Last terms audit:** 2026-11-12

---

## Sources at a glance

| | India — CIOINS | UK — FOS | Ireland — FSPO |
|---|---|---|---|
| **Publisher** | Council for Insurance Ombudsmen | Financial Ombudsman Service | Financial Services and Pensions Ombudsman |
| **What is used** | Health-insurance (mediclaim) awards | Insurance decisions, filtered to medical/health | Decisions for "Health, Accident and Other" products |
| **Outcome label** | Free text in the award order, mapped by rules | Upheld / Not upheld (listing metadata) | Rejected / Partially / Substantially / Upheld (metadata) |
| **Role** | Primary target domain | Training volume | Clean labels, structured reasons |
| **Entry point** | [cioins.co.in/AwardsHArchive](https://cioins.co.in/AwardsHArchive) | [FOS decisions search](https://www.financial-ombudsman.org.uk/decisions-case-studies/ombudsman-decisions/SearchDecisions) | [fspo.ie](https://www.fspo.ie) |

---

## Terms of use and usage decision

| Source | Terms say | Decision | Status |
|---|---|---|---|
| **FSPO** | Re-use permitted free of charge under PSI rules, including copying and non-commercial research, with attribution and accurate reproduction | Collect, train, index; publish anonymised derived text with attribution | ✅ Cleared |
| **FOS** | Storing material in any electronic retrieval system needs prior permission | Do not collect until permission is granted | ⏳ Permission ⟨requested on … / granted on … / refused⟩ |
| **CIOINS** | Unauthorised copying or use of site content is prohibited | Do not collect until authorisation is granted | ⏳ Permission ⟨requested on … / granted on … / refused⟩ |

**Default when terms are unclear or permission is limited:** collect for local research use only; publish code, aggregate statistics and model weights; do **not** publish the processed text.

Full checklist, robots.txt capture, permission-request template and reply log: [`docs/data/terms-of-use-audit.md`](docs/data/terms-of-use-audit.md).

---

## How the data is handled

| Rule | Where it is enforced |
|---|---|
| At most one request every 2–3 s, single-threaded, User-Agent names the project and a contact | Collectors (`src/claimsense/collect/`), [`collection-runbook.md`](docs/data/collection-runbook.md) |
| Raw PDFs and pages stay on the author's laptop; `data/raw/` is git-ignored | `.gitignore`, pre-commit guard, CI `guard` job |
| Names, addresses, contacts, reference numbers, providers removed before any processed text is written; insurer names, conditions and amounts kept | [`anonymisation-spec.md`](docs/data/anonymisation-spec.md) (PR 6) |
| The model sees only facts and the insurer's position, never findings or the award | [`leakage-contract.md`](docs/architecture/leakage-contract.md), leak probes |
| Temporal split: train ≤ 2023, validation 2024, test 2025+ | [`dataset-versioning.md`](docs/data/dataset-versioning.md) (PR 7) |

---

## Supporting documents (explanations only, never labels)

| Document | Use |
|---|---|
| IRDAI standardised exclusion list (Excl01–Excl18) | Name the standard exclusion a precedent turned on |
| Insurer Customer Information Sheets | Show where similar clauses appear in real policies |
| IRDAI annual reports | Problem statistics in the README |

---

## Attribution

> Contains information from decisions of the Financial Services and Pensions Ombudsman (Ireland), © FSPO, re-used under the Re-use of Public Sector Information Regulations. Text has been anonymised and shortened by ClaimSense and is not reproduced in its original form.

FOS and CIOINS attribution lines are added here only once permission is granted (wording in `terms-of-use-audit.md` §5).

---

## Known limitations of the data

Selection bias (only escalated, decided disputes), jurisdiction mismatch (UK and Irish rules differ from India's), label noise in free-text Indian awards, and drift over time. Each is measured or stated in [`docs/responsible-ai/limitations.md`](docs/responsible-ai/limitations.md); per-version counts and gaps are in [`DATA_CARD.md`](DATA_CARD.md).

---

<sub>ClaimSense is not affiliated with or endorsed by CIOINS, FOS or FSPO. This summary records the project's reading of each publisher's terms for planning purposes; it is not legal advice.</sub>
