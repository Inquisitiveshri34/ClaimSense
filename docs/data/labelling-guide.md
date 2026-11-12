# ClaimSense — Labelling Guide

> How every decision gets exactly one of three labels — **Upheld, Partially upheld, Rejected** — or is excluded. Covers label definitions, the mapping from each source's wording, exclusion rules, how unmapped wording is handled, the rejection-reason tag, and the label audit.

**Author:** Diya Shrivastava · **Owning PR:** 6 · **Status:** Planned

**Related:** `04-data-sources.md` §4, `leakage-contract.md` §2 (award → label only), `manual-audit-protocol.md` §4, FR-06, risk R6, design decision D3.

---

## 1. Label definitions

Labels describe **what the ombudsman ordered the insurer to do about the claim**, measured against what the complainant asked for.

| Label | Definition | Test question |
|---|---|---|
| `upheld` | The insurer is directed to pay the claim in full (or the full amount in dispute), with or without interest | Did the complainant get everything they disputed? |
| `partially_upheld` | The insurer is directed to pay part of the disputed amount, pay ex-gratia, or reconsider/re-process the claim | Did the complainant get something, but not all? |
| `rejected` | The complaint is dismissed; the insurer's decision stands; no payment ordered | Did the complainant get nothing? |
| *excluded* | No decision on the merits | Was the dispute actually decided? |

`label_binary` = `label != rejected` ("any payment ordered").

### Edge rules

| Situation | Label |
|---|---|
| Full claim upheld but a deductible/co-pay applied as per policy | `upheld` |
| Insurer ordered to pay a "proportionate" amount (room-rent capping) | `partially_upheld` |
| Insurer ordered to pay only interest for delay, claim already paid | **excluded** (`delay_only`) — not a repudiation dispute |
| Insurer ordered to reconsider with no amount stated | `partially_upheld` |
| Ex-gratia payment with complaint otherwise dismissed | `partially_upheld` |
| Compensation for distress only, claim refusal upheld | `rejected` (claim outcome is what is labelled); flagged `distress_award = true` in the log |
| Multiple claims in one award, different outcomes | `partially_upheld` if any paid and any refused; else the shared outcome |
| FOS: "upheld in part" written in text though listing says Upheld | Use the **text**; log the conflict |

---

## 2. Mapping by source

The label is read from the **award section and source metadata only** — never from findings.

### 2.1 FSPO (metadata field `Outcome`)

| FSPO outcome | Label |
|---|---|
| Upheld | `upheld` |
| Substantially upheld | `upheld` |
| Partially upheld | `partially_upheld` |
| Rejected | `rejected` |

Check: if the award text orders a sum below the claim for a "Substantially upheld" case, keep `upheld` (FSPO's own judgement) but log it for the audit sample.

### 2.2 FOS (listing outcome + award text)

| FOS listing | Award text pattern | Label |
|---|---|---|
| Upheld | Pay the claim / settle the claim in line with the policy | `upheld` |
| Upheld | Reconsider the claim / pay part / pay £X less … | `partially_upheld` |
| Upheld | Pay compensation only (claim decline stands) | `rejected` + `distress_award` |
| Not upheld | — | `rejected` |

Because FOS has no "partial" listing value, every FOS `Upheld` goes through the award-text rules. Patterns live in `config.yaml` → `label.fos.partial_cues`.

### 2.3 CIOINS (award text, free wording)

| Pattern (case-insensitive, examples) | Label |
|---|---|
| "complaint is allowed", "insurer is directed to settle/pay the claim of ₹X" where X equals claimed amount (±2%) | `upheld` |
| "directed to pay ₹X" where X < claimed amount; "partially allowed"; "ex-gratia"; "proportionate"; "reconsider/re-examine the claim" | `partially_upheld` |
| "complaint is dismissed", "repudiation is upheld/sustained/justified", "no relief", "does not warrant interference" | `rejected` |

Amount comparison needs the claimed amount from facts and the awarded amount from the award; both are extracted with an INR amount regex (`₹`, `Rs.`, `Rs`, `INR`, lakh notation `1,20,000`, `1.2 lakh`). If either is missing and no other cue fires, the wording is **unmapped**, not guessed.

---

## 3. Exclusions

| Reason code | Detected by (examples) | Source |
|---|---|---|
| `non_entertainable` | "not entertainable", "outside the scope of Rule 13/14", "time-barred", "sub judice", "already decided by another forum" | CIOINS, FSPO |
| `withdrawn` | "withdrawn by the complainant", "complainant did not appear" + closed | All |
| `settled` | "settled by the insurer before the hearing", "resolved by mediation", "recommendation accepted" | All |
| `delay_only` | Only interest for delay ordered | All |
| `not_health` | Product turns out not to be health on reading | All |
| `jurisdiction` | Complaint against a broker/agent, not a claim decision | All |

Excluded documents are logged and counted in the funnel; they never enter `data/processed/`. Note: CIOINS "recommendations" (mediated settlements under Rule 16) are **not** awards; they are excluded as `settled`.

---

## 4. Unmapped wording

1. The extractor never assigns a default label.
2. Anything not matched by §2 or §3 is written to `data/interim/labelled/_unmapped.csv`: `doc_id, source, office, award_excerpt (≤ 300 chars), candidate_rule`.
3. Resolve by hand in batches: read the award, decide the label, and **add or change a rule** so the same wording maps automatically next time. Do not hand-label individual documents outside a rule.
4. Each rule change bumps `label.rules_version` and is recorded below.
5. The PR 6 merge requires `_unmapped.csv` to be empty, or remaining rows explicitly excluded as `ambiguous` with a count in the data card.

### Rule change log

| Date | Rules version | Source | Change | Docs affected |
|---|---|---|---|---|
| | v1 | All | Initial rules from this guide | — |

---

## 5. Rejection-reason tag

`rejection_reason` describes **why the insurer rejected the claim**, read from complaint + insurer position only (it is an input-side attribute used for breakdowns and the Precedent Explorer, so it must not use findings).

| Value | Assign when the insurer's stated reason is… | Cue examples |
|---|---|---|
| `non_disclosure` | Pre-existing disease not disclosed / misrepresentation at proposal | "PED", "non-disclosure", "suppression of material facts" |
| `waiting_period` | Treatment fell within an initial, specific-disease or PED waiting period | "30-day", "two-year waiting", "specific waiting period" |
| `exclusion` | A named policy exclusion | "excluded under clause", "Excl", "cosmetic", "alcohol" |
| `not_medically_necessary` | Hospitalisation not required / OPD-able / < 24 h without day-care listing | "could be done on OPD basis", "no active line of treatment" |
| `documentation` | Missing or late documents, late intimation | "documents not submitted", "late intimation" |
| `other` | Anything else, or several reasons with none dominant | — |

Multi-reason rule: take the **first** reason the insurer gives; if the insurer gives a primary and a fallback ("and in any case…"), take the primary. Accuracy of this tag is part of the label audit.

---

## 6. Audit (gate for PR 6)

- 100 labelled documents, drawn per `manual-audit-protocol.md` §4 (stratified by source and label, CIOINS over-sampled).
- Reviewer reads the **award** and records the correct label and rejection reason, without seeing the extractor's output first.
- **Label accuracy ≥ 95%** (R6). Rejection-reason accuracy is reported (target ≥ 85%, not a gate).
- Every error becomes a rule change or a documented exclusion; then the audit is re-scored on the same 100.
- Result recorded in the PR and in the data card ("label accuracy: X% on 100 hand-checked documents").
