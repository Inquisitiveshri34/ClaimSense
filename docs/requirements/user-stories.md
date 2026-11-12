# ClaimSense — User Stories

> Stories for the three personas in `01-project-overview.md`: the **policyholder** with a rejected claim, the **caregiver** handling a claim for someone else, and the **advisor** helping others. Each story is traced to the requirements that satisfy it.

**Author:** Diya Shrivastava

---

## 1. Conventions

- **Format:** *As a ⟨persona⟩, I want ⟨capability⟩, so that ⟨benefit⟩.*
- **IDs:** `US-P*` policyholder, `US-C*` caregiver, `US-A*` advisor.
- **Priority (MoSCoW):** **Must** = required for v1.0; **Should** = v1.0 if time allows; **Could** = candidate for v2 (`scope.md`).
- **Traces to:** FR/NFR IDs from `functional-requirements.md` and `non-functional-requirements.md`.
- Stories marked **⚠ Gap** have no covering FR yet; see §6.

---

## 2. Persona — Policyholder with a rejected claim

| | |
|---|---|
| **Who** | Adult with an individual or family mediclaim policy whose hospitalisation claim was fully or partly repudiated |
| **Situation** | Has the rejection letter and a rough idea of the policy wording; has never read an ombudsman decision |
| **Goal** | Decide whether to file a complaint with the Insurance Ombudsman |
| **Pain points** | Policy language is opaque; does not know if the insurer's reason usually holds up; worried about wasting time |
| **Success looks like** | A clear, honest estimate with real cases behind it — or a clear "we can't tell" |

| ID | Story | Priority | Traces to |
|---|---|---|---|
| US-P1 | As a policyholder, I want to describe my claim in my own words — what happened, what the policy says and why the insurer rejected it — so that I don't need to know legal terms to get an answer. | Must | FR-14, NFR-12 |
| US-P2 | As a policyholder, I want to see the likely outcome (*Upheld*, *Partially upheld* or *Rejected*), so that I know whether a complaint is worth filing. | Must | FR-11, FR-14 |
| US-P3 | As a policyholder, I want a probability that means what it says, so that I can weigh the effort of complaining against my real chance of success. | Must | FR-12, NFR-03 |
| US-P4 | As a policyholder, I want to see past cases similar to mine, so that I can trust the prediction is based on real decisions. | Must | FR-13, FR-15 |
| US-P5 | As a policyholder, I want a short explanation where every point refers to a past case, so that I understand *why* without being misled by invented reasons. | Must | FR-16, NFR-04 |
| US-P6 | As a policyholder, I want the system to tell me when it does not have enough similar cases, so that I am not misled by a confident-looking guess. | Must | FR-17 |
| US-P7 | As a policyholder, I want to be told clearly that this is not legal advice, so that I know the ombudsman still decides my case on its own facts. | Must | FR-19 |
| US-P8 | As a policyholder in India, I want to see which country each precedent comes from, so that I can give more weight to Indian decisions. | Should | FR-13 (metadata) · **⚠ Gap G1** |
| US-P9 | As a policyholder, I want to see my chance of getting *any* payment, so that a partial settlement still counts as worth pursuing. | Could | FR-06 (`label_binary`) · **⚠ Gap G2** |

---

## 3. Persona — Family member or caregiver

| | |
|---|---|
| **Who** | Son, daughter, spouse or carer managing a claim for a patient who cannot handle it themselves |
| **Situation** | Juggling hospital paperwork; received the rejection second-hand; time-poor and stressed |
| **Goal** | Understand the rejection reason and how similar cases have gone, then explain it to the family |
| **Pain points** | Unfamiliar terms (non-disclosure, waiting period, exclusion); cannot read long PDFs; worried about the patient's privacy |
| **Success looks like** | A fast, plain answer they can repeat to the family, with examples |

| ID | Story | Priority | Traces to |
|---|---|---|---|
| US-C1 | As a caregiver, I want to get an answer in a few seconds, so that I can check it between hospital and work. | Must | NFR-06 |
| US-C2 | As a caregiver, I want the outcome, probability and explanation in plain words, so that I can explain them to the patient and family. | Must | NFR-12, FR-16 |
| US-C3 | As a caregiver, I want to browse past decisions by rejection reason (e.g. waiting period, non-disclosure), so that I understand how that reason is usually treated. | Must | FR-18 (Precedent Explorer) |
| US-C4 | As a caregiver, I want precedents to show the medical condition and claim amount but no names or addresses, so that I can compare cases without exposing other families. | Must | FR-07, NFR-02 |
| US-C5 | As a caregiver, I want precedents to come only from decisions made before my case, so that the comparison is fair and realistic. | Must | FR-15 |
| US-C6 | As a caregiver, I want to see the disclaimer on every page I land on, so that no one in the family mistakes the result for a ruling. | Must | FR-19 |

---

## 4. Persona — Insurance advisor or consumer-help volunteer

| | |
|---|---|
| **Who** | Independent advisor, NGO consumer-help volunteer or law-student helper who assists several people a week |
| **Situation** | Understands insurance terms; needs relevant precedents quickly and needs to judge how far the tool can be trusted |
| **Goal** | Find strong precedents for each person they help and set honest expectations |
| **Pain points** | Searching ombudsman PDFs by hand is slow; tools that overclaim damage their credibility |
| **Success looks like** | Fast, filterable precedents and a transparent account of where the model fails |

| ID | Story | Priority | Traces to |
|---|---|---|---|
| US-A1 | As an advisor, I want to filter past decisions by rejection reason, insurer type and year, so that I can find the precedents most relevant to the person I'm helping. | Must | FR-18 (Precedent Explorer), FR-13 |
| US-A2 | As an advisor, I want each precedent to show its source ombudsman, decision year, outcome and the findings it turned on, so that I can judge its relevance myself. | Must | FR-13, FR-14 |
| US-A3 | As an advisor, I want to see the model's test metrics, calibration plot and known failure modes, so that I know when to trust it and when not to. | Must | FR-18 (Model Card), NFR-11 |
| US-A4 | As an advisor, I want to see performance broken down by country, rejection reason, insurer type and claim size, so that I know if it is weaker for the cases I see most. | Must | FR-20, NFR-11 |
| US-A5 | As an advisor, I want to see the dataset's size, sources, date range and class balance, so that I understand what the predictions are based on. | Must | FR-18 (Data Explorer), FR-09 |
| US-A6 | As an advisor, I want to know the abstain rate, so that I can tell people how often the tool will decline to answer. | Should | FR-17, NFR-11 |
| US-A7 | As an advisor, I want the explanation to name the standard IRDAI exclusion a precedent turned on, so that I can point people to the exact clause type. | Could | **⚠ Gap G3** |

---

## 5. Story map

| User step | Policyholder | Caregiver | Advisor |
|---|---|---|---|
| **Describe the case** | US-P1 | US-C1 | — |
| **Get a prediction** | US-P2, US-P3, US-P9 | US-C2 | — |
| **See precedents** | US-P4, US-P8 | US-C3, US-C4, US-C5 | US-A1, US-A2 |
| **Understand why** | US-P5 | US-C2 | US-A7 |
| **Know the limits** | US-P6, US-P7 | US-C6 | US-A3, US-A4, US-A5, US-A6 |

---

## 6. Gaps found while writing stories

| Gap | Story | Issue | Proposed resolution |
|---|---|---|---|
| **G1** | US-P8 | Risk R13 says "show precedent country", but no FR requires the app to display it. | Add to FR-14 / FR-18 notes: each precedent displays source and country. Verify in PR 17. |
| **G2** | US-P9 | Design decision D3 creates a binary "any payment" view, but FR-14 does not return it. | Keep as an evaluation metric (PR-AUC) in v1; move user-facing display to the v2 backlog (`scope.md`). |
| **G3** | US-A7 | `04-data-sources.md` §6 lists the IRDAI exclusion list (Excl01–Excl18) as supporting material, but no PR builds the mapping. | v2 backlog unless PR 13 has spare time. |
