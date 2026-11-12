# ClaimSense — Data Sources

> Three public ombudsman databases supply real decisions with real outcomes: **India (CIOINS)**, **UK (FOS)** and **Ireland (FSPO)**. This file records what each source holds, how it will be collected, how outcomes become labels, and how personal data is removed. Terms of use are **verified in PR 2** before any bulk download.

**Author:** Diya Shrivastava

---

## 1. Sources at a glance

| | India — CIOINS | UK — FOS | Ireland — FSPO |
|---|---|---|---|
| **Publisher** | Council for Insurance Ombudsmen | Financial Ombudsman Service | Financial Services and Pensions Ombudsman |
| **Content** | Monthly award PDFs by insurance type; separate health-awards archive | Final decisions since 1 April 2013 (382,298 listed at last check) | Legally binding decisions as PDFs, with a searchable database and themed digests |
| **Health coverage** | Group, individual and overseas mediclaim awards | Filter by product "Insurance", then keyword-filter for medical/health | Product "Health, Accident and Other" |
| **Outcome label** | Stated in the award order (free text) | Upheld / Not upheld in listing metadata | Rejected / Partially upheld / Upheld / Substantially upheld in metadata |
| **Extra metadata** | Office, award number, insurer, policy type | Date, business name, product | Sector, product, conduct complained of, year |
| **Format** | PDF, layouts vary by office | HTML listing + decision pages | PDF with metadata page |
| **Role in project** | Primary target domain | Training volume | Clean labels, structured reasons |
| **Main risk** | Fewer, shorter texts; complainant names and addresses in PDFs | Most decisions are not health | Smaller volume |

**Entry points**

- India: [CIOINS health awards archive](https://cioins.co.in/AwardsHArchive), monthly award PDFs under `cioins.co.in/AwardsMonthwise/`
- UK: [FOS ombudsman decisions search](https://www.financial-ombudsman.org.uk/decisions-case-studies/ombudsman-decisions/SearchDecisions)
- Ireland: [FSPO decisions](https://www.fspo.ie) and the [health-insurance Digest of Decisions, Vol. 8](https://www.fspo.ie/documents/Ombudsmans_Digest_of_Decisions_Vol8.pdf)

---

## 2. Terms-of-use checklist (PR 2)

To be filled after reading each site's terms, copyright notice and robots.txt. **Nothing is bulk-downloaded until every box for that source is ticked.**

| Check | CIOINS | FOS | FSPO |
|---|---|---|---|
| Terms of use / copyright notice read and summarised | [ ] | [ ] | [ ] |
| robots.txt allows the paths used | [ ] | [ ] | [ ] |
| Automated access permitted (or permission requested) | [ ] | [ ] | [ ] |
| Redistribution of derived, anonymised text permitted? | [ ] | [ ] | [ ] |
| Attribution wording recorded | [ ] | [ ] | [ ] |

**Default if terms are unclear:** collect for local research use only, publish code + aggregate statistics + model weights, and do **not** publish the processed text dataset.

---

## 3. Collection plan

### Shared rules for every collector

- **Rate limit:** at most 1 request every 2–3 seconds, single-threaded.
- **User-Agent:** names the project and a contact email.
- **Resumable:** every file is recorded in a manifest; a re-run skips what is already downloaded.
- **Integrity:** SHA-256 hash per file; duplicates detected by hash.
- **Raw data stays local:** `data/raw/` is git-ignored and never published.

### Manifest schema (one row per decision)

| Field | Example | Notes |
|---|---|---|
| `doc_id` | `cioins-2023-05-1004-0056` | Stable, source-prefixed |
| `source` | `cioins` / `fos` / `fspo` | |
| `url` | Original document URL | Kept for traceability, not shown in the app |
| `decision_date` | `2023-05-12` | Drives the temporal split |
| `insurer` | Insurer name | Public party, kept |
| `product` | `individual_mediclaim` | Normalised across sources |
| `outcome_raw` | Source's own wording | Before mapping |
| `file_sha256` | Hash | Dedup + integrity |
| `fetched_at` | Timestamp | |

### Per-source approach

| Source | Steps |
|---|---|
| **CIOINS** (PR 3) | Read the health archive's month list → fetch each month's award PDFs → record office, award number and insurer → filter to health policy types |
| **FOS** (PR 4) | Page through the decisions listing filtered to insurance → keep listing metadata (date, business, product, outcome) → fetch decision pages → keyword-filter to medical/health |
| **FSPO** (PR 4) | Page through decisions filtered to health products → download PDFs → keep the metadata block (outcome, conduct complained of, year) |

---

## 4. From document to label

### Outcome mapping

| Project label | CIOINS wording (examples) | FOS | FSPO |
|---|---|---|---|
| **Upheld** | Complaint allowed; insurer directed to pay in full | Upheld | Upheld, Substantially upheld |
| **Partially upheld** | Part payment awarded; insurer directed to reconsider | — (rare; checked by hand) | Partially upheld |
| **Rejected** | Complaint dismissed; repudiation sustained | Not upheld | Rejected |
| *Excluded* | Non-entertainable, withdrawn, settled before award | — | — |

Unmapped wording is logged and resolved by hand, never guessed. A 100-document sample is double-checked by hand to measure label accuracy.

### Section boundaries (input vs label)

| Section | Kept as | Typical marker |
|---|---|---|
| Complaint / background | Input | "The complaint", "Brief facts" |
| Insurer's position | Input | "The insurer's case", "Respondent's submission" |
| Findings / reasoning | Explanation reference only | "My findings", "Observations", "What I've decided and why" |
| Award / decision | Label | "Award", "My final decision", "Decision" |

Markers are per source and per office; they are learned and tested in PR 5.

---

## 5. Anonymisation (PR 6)

Ombudsman decisions describe real people's medical and financial disputes. Indian award PDFs include the complainant's **name and address**. Personal data is removed **before** any processed text is written.

| Data | Action | Method |
|---|---|---|
| Complainant / family names | Replace with `[PERSON]` | Presidio NER + name list from the award header |
| Addresses, PIN codes, cities below state level | Replace with `[ADDRESS]` | Presidio + Indian PIN-code regex |
| Phone numbers, emails | Replace with `[CONTACT]` | Regex |
| Policy, claim, award and complaint reference numbers | Replace with `[REF]` | Source-specific regex |
| Dates of birth, exact ages | Generalise to age band | Regex |
| Hospital and doctor names | Replace with `[PROVIDER]` | NER + keyword list |
| Insurer names | **Kept** | Public parties to the dispute |
| Medical condition and claim amounts | **Kept** | Needed for the task; not identifying once names are removed |

**Checks**

- 0 PII hits on a 100-document manual sample (PR 6 done-when).
- Automated scan of the full processed set for leftover numbers matching phone, PIN or policy patterns.
- `doc_id` links back to raw files only on the local machine.

---

## 6. Supporting documents (explanations only, not labels)

| Document | Use |
|---|---|
| IRDAI standardised exclusion list (Excl01–Excl18) | Name the standard exclusion a precedent turned on |
| Insurer Customer Information Sheets (CIS) | Show users where similar clauses appear in real policies |
| IRDAI annual reports | Problem statistics in the README and overview |

---

## 7. Dataset versioning

- Processed dataset saved as Parquet in `data/processed/`, versioned with a content hash (or DVC).
- Each version has a **data card**: sources, date range, counts per source and class, anonymisation method, known gaps.
- Temporal split fixed at build time: **train ≤ 2023, validation 2024, test 2025+**. It is rebuilt only with a new dataset version.

---

## 8. Known limitations

- **Selection bias:** only disputes that reached an ombudsman are included; most rejected claims never do.
- **Jurisdiction mismatch:** UK and Irish policies, regulations and wording differ from Indian ones; reported as a domain-shift result, not hidden.
- **Label noise:** free-text Indian awards are mapped by rules; label accuracy is measured and reported.
- **Coverage drift:** policy rules and regulations change over time; the temporal split measures this.
