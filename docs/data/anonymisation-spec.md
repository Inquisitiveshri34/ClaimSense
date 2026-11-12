# ClaimSense — Anonymisation Specification

> What is removed from every decision before any processed text is written, how it is detected, what replaces it, what is deliberately kept, and how the result is checked. Indian awards name complainants and give addresses; nothing downstream of this step may contain personal data.

**Author:** Diya Shrivastava · **Owning PR:** 6 · **Status:** Planned

**Related:** `04-data-sources.md` §5, `data-flow.md` Stage 4, `manual-audit-protocol.md` §5, FR-07, NFR-02, risk R5, design decision D10.

---

## 1. Principles

1. **Remove before write.** The scrubber runs on in-memory segments; only scrubbed text is written to `data/interim/labelled/` (FR-07c).
2. **Over-remove rather than under-remove.** A false positive costs a few words of context; a false negative exposes a family's medical history.
3. **Keep what the task needs.** Conditions, treatments, amounts, durations and insurer names stay.
4. **Same entity, same token within a document.** Two different people become `[PERSON_1]`, `[PERSON_2]`, so the text still reads.
5. **No reversible mapping is stored** outside the local `raw/` zone.

---

## 2. Entities

| # | Entity | Token | Detector | Notes |
|---|---|---|---|---|
| E1 | Complainant, family, nominee, agent names | `[PERSON_n]` | Header name list + Presidio `PERSON` + honorific regex | Header list = names parsed from the award's party block; all their tokens (first, last, initials) are replaced everywhere |
| E2 | Ombudsman and staff names, signatures | `[PERSON_n]` | Signature block regex + Presidio | The ombudsman is a public official, but removing the name costs nothing |
| E3 | Doctor names | `[PROVIDER]` | `Dr\.?\s+[A-Z]…` regex + Presidio `PERSON` near medical cue words | |
| E4 | Hospital, clinic, lab names | `[PROVIDER]` | Keyword list (`Hospital`, `Nursing Home`, `Clinic`, `Medical Centre`, `Diagnostics`, `Lab`) + preceding capitalised tokens; Presidio `ORG` near those words | Hospital **type** words are kept generically: "a private hospital" |
| E5 | Street addresses, localities, villages, districts, cities below state | `[ADDRESS]` | Presidio `LOCATION` + address cue regex (`Flat`, `Plot`, `H.No`, `Sector`, `Nagar`, `Road`, `Street`, `Lane`) | **State and country kept** |
| E6 | Indian PIN codes | `[ADDRESS]` | `\b[1-9][0-9]{2}\s?[0-9]{3}\b` near address context | Without context the 6-digit rule could hit amounts; context window ±40 chars |
| E7 | UK postcodes, Irish Eircodes | `[ADDRESS]` | Standard postcode / Eircode regex | |
| E8 | Phone numbers | `[CONTACT]` | Indian mobile `(\+91[\s-]?)?[6-9]\d{9}`, landline with STD code, UK/IE formats | |
| E9 | Email addresses | `[CONTACT]` | RFC-lite regex | |
| E10 | Policy, claim, complaint, award, membership, TPA ID numbers | `[REF]` | Cue word (`Policy No`, `Claim No`, `Complaint No`, `Award No`, `Ref`, `ID`, `UHID`, `IP No`) + alphanumeric run; source-specific formats (CIOINS award ID, FOS `DRN-…`, FSPO reference) | |
| E11 | Government IDs (Aadhaar, PAN, passport, NHS, PPSN) | `[REF]` | Format regex (Aadhaar 12 digits grouped 4-4-4; PAN `[A-Z]{5}\d{4}[A-Z]`; PPSN `\d{7}[A-Z]{1,2}`) | Should never appear; scrubbed anyway |
| E12 | Bank account, IFSC, card numbers | `[REF]` | Cue word + digit run; IFSC regex; Luhn check for cards | |
| E13 | Dates of birth | `[DOB]` | Cue (`DOB`, `date of birth`, `born on`) + date | |
| E14 | Exact ages | age band, e.g. `[AGE_40-49]` | `\b\d{1,3}\s?(years?|yrs?)[\s-]?old\b`, `aged \d+`, `\d+ y/o` | Ten-year bands; under-18 → `[AGE_MINOR]` |
| E15 | Employer names (group mediclaim) | `[EMPLOYER]` | Cue (`employed with`, `employees of`, `group policy issued to`) + Presidio `ORG` | Large employers can identify small groups |
| E16 | Vehicle registration, URLs, IPs | `[REF]` | Regex | Rare; cheap to catch |

Dates **other than** DOB (admission, discharge, policy start, claim date) are kept: the gap between policy start and diagnosis decides waiting-period and non-disclosure disputes. They are generalised to **month and year** (`12/03/2023` → `03/2023`), which keeps intervals readable while removing a precise date.

---

## 3. Kept on purpose

| Kept | Why |
|---|---|
| Insurer names (public companies) | Parties to a public dispute; needed for `insurer_type` and breakdowns |
| TPA names (companies) | Same |
| Medical conditions, procedures, medicines | The core of the dispute |
| Claim, awarded and sum-insured amounts | Needed for the task and `claim_amount_band` |
| Durations and month/year dates | Waiting-period logic |
| Policy clause text and exclusion names | Needed for explanations |
| State / country | Jurisdiction context |
| Gender words (he/she) | Needed for readable text; not identifying alone |

Rare-condition risk: a very rare disease plus a small town plus a date can identify someone even without names. Mitigation: towns are already removed (E5), dates are month/year, and the PII audit (§6) checks for this combination explicitly.

---

## 4. Order of operations

1. Parse the party/header block → build the document's **name list** (E1) and **reference list** (E10).
2. Run regex detectors (E6–E14, E16) → spans.
3. Run Presidio (`en_core_web_lg` NER + custom recognisers for Indian names and address cues) → spans.
4. Merge overlapping spans; the **longer** span wins; on ties, the stricter token wins (`[PERSON]` over `[PROVIDER]`).
5. Replace names from the name list **everywhere** in all four segments, including partial matches (surname alone, initials `R. K.`).
6. Replace spans; assign `_n` indices per document.
7. Generalise dates (§2) and ages (E14).
8. Post-check regexes (§5). Any hit → document goes to `_pii_quarantine/` and is not written.

Presidio score threshold: 0.4 (low, per principle 2); tuned on the PR 6 dev sample and recorded in `config.yaml` → `anonymise.presidio_threshold`.

---

## 5. Automated post-check (NFR-02b)

Runs on every scrubbed document and again on the full processed dataset in CI (`tests/test_schema.py`).

| Pattern | Regex family | Allowed hits |
|---|---|---|
| Indian mobile / landline | E8 | 0 |
| Email | E9 | 0 |
| PIN code with address cue | E6 | 0 |
| UK postcode / Eircode | E7 | 0 |
| Policy/claim number cue + ≥ 6 alphanumerics | E10 | 0 |
| Aadhaar / PAN / PPSN format | E11 | 0 |
| Honorific + capitalised word (`Mr X`, `Smt. Y`, `Shri Z`) not followed by a token | E1 | 0 |
| `Dr` + capitalised word | E3 | 0 |

---

## 6. Manual check (NFR-02a, gate for PR 6)

- 100 processed documents, drawn per `manual-audit-protocol.md` §5.
- Reviewer reads `facts_text` and `findings_text` fully and records every remaining identifier with its entity type.
- **Gate: 0 hits.** One hit fails the gate: fix the detector, re-run the scrubber on everything, and draw a **new** sample of 100 (not the same one).
- Also recorded (not gated): over-removal rate — share of tokens wrongly replaced (e.g. a disease named after a person: "Parkinson's" → keep via allowlist of eponymous conditions).

### Allowlist (never replaced)

Eponymous conditions and tests (Parkinson, Alzheimer, Hodgkin, Crohn, Down syndrome, Bell's palsy, Guillain-Barré, Hashimoto, Cushing, Addison, Wilms…), drug names, insurer and TPA names, regulator names (IRDAI, FCA, Central Bank of Ireland), statutes. Stored in `config.yaml` → `anonymise.allowlist`.

---

## 7. Tests (PR 6)

| Test | Checks |
|---|---|
| `test_anonymise_entities.py` | One fixture per entity E1–E16 → correct token |
| `test_anonymise_kept.py` | Insurer names, conditions, amounts, month/year dates survive |
| `test_anonymise_consistency.py` | Same person → same `_n` across all four segments |
| `test_anonymise_allowlist.py` | "Parkinson's disease" kept; "Mr Parkinson" replaced |
| `test_pipeline_order.py` | Nothing in `data/interim/labelled/` or `data/processed/` before scrubber runs (FR-07c) |
| `test_pii_scan.py` | Post-check regexes find 0 hits on processed fixtures |
