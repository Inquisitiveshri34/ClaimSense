# ClaimSense — Responsible Use

> Who ClaimSense is for, what it may and may not be used for, how it can hurt the people who use it, and the exact words the app shows to keep those harms small. Covers the disclaimer and every other piece of fixed user-facing text, intended and unintended uses, a harm register, and the presentation rules the Streamlit app must follow.

**Author:** Diya Shrivastava · **Owning PR:** 17 · **Status:** Planned

**Related:** FR-14, FR-17, FR-18, FR-19, NFR-11, NFR-12, design decisions D5, D6, D8, risks R12, R13, `../PRD.md` §3, `../user-stories.md`, `../modelling/abstention-policy.md` §7, `../evaluation/fairness-analysis-plan.md` §2 and §7, `privacy-impact-assessment.md` §9, `limitations.md`, `../scope.md` §3.

---

## 1. Principle

ClaimSense tells a person **how similar past disputes were decided**. It does not tell them what will happen to their claim, and it does not tell them what to do.

Its users are mostly people with a rejected medical bill, often stressed, often not experts, and sometimes deciding under a deadline. For them a confident wrong number can do more harm than no number: someone may drop a claim they would have won. Every rule below follows from that.

---

## 2. Disclaimer and fixed text

All strings live in `src/claimsense/app/text.py` so that one test can check them and wording never drifts between pages.

### 2.1 Disclaimer (FR-19, every page)

The canonical text, unchanged from `functional-requirements.md`:

> **ClaimSense describes how similar past cases were decided. It is not legal advice; the ombudsman decides each case on its own facts.**

| Rule | Detail |
|---|---|
| Placement | Top of every page, above any result. On Predict it also repeats directly under the result |
| Style | Normal body text in a bordered box; not collapsed, not in a footer, not in grey small print |
| Abstentions | Shown on every abstention screen too (`PRD.md` §5.1) |
| Exports | Any copy/download of a result carries the disclaimer as its first line |

### 2.2 Extended notice (Predict page, under the disclaimer)

> ClaimSense learned from published decisions of insurance ombudsmen in India, the UK and Ireland. It cannot see your policy documents, medical records or letters, and the ombudsman will. Use it to understand your situation and to decide what questions to ask, not to decide whether to complain. If you are unsure, you can contact the Insurance Ombudsman, your insurer's grievance officer, or a consumer-help organisation. Complaint schemes have time limits and usually require you to complain to the insurer first, so check the rules early.

### 2.3 Result wording

| Element | Text pattern |
|---|---|
| Headline | "In past cases like yours, the ombudsman most often **⟨upheld the complaint / partly upheld it / rejected it⟩**." |
| Probability | "ClaimSense estimates about **⟨7 in 10⟩** similar cases ended this way." (calibrated probability, rounded to the nearest 10%, with the exact figure on hover) |
| All three outcomes | Small bar for each of the three calibrated class probabilities, always shown together |
| Precedents | Each card shows **country and ombudsman**, decision year, outcome and similarity (gap G1) |
| Explanation header | "What the similar decisions said" |
| Empty explanation | "No explanation could be supported by the precedents." (`pipeline-interface.md` §2) |
| Explainer down | "The explanation is unavailable right now. The estimate and similar cases above are unaffected." |

### 2.4 Abstention messages

| Code | Message |
|---|---|
| `INPUT_TOO_SHORT` | "Please add more detail: what was treated, what the policy says, and the reason the insurer gave for rejecting the claim." |
| `UNSUPPORTED_LANGUAGE` | "ClaimSense currently understands English only." |
| `OFF_TOPIC` | "This doesn't look like a rejected health-insurance claim, which is the only kind of case ClaimSense has learned from." |
| `NO_PRECEDENTS` | "ClaimSense hasn't seen enough past decisions like this one to give an estimate." |
| `LOW_CONFIDENCE` | "Similar past cases went different ways, so ClaimSense won't give an estimate. The closest cases are shown below so you can read how they were decided." |

None of these messages suggests the claim is weak. An abstention is about **ClaimSense's** limits, not the user's case.

### 2.5 Flagged-slice note

When the input's stated country or amount falls in a slice flagged in `fairness-analysis-plan.md` §6:

> "ClaimSense has been less accurate on past cases like this one ⟨from Ireland / with claims of this size⟩. Treat this estimate with extra caution."

The note is triggered only by details the user typed, never inferred about the person.

### 2.6 Jurisdiction note

When more than half of the shown precedents come from a different country than the one the user selected:

> "Most of the closest past cases are from ⟨the UK / Ireland⟩, where the rules and policies differ from India's."

### 2.7 Privacy notice

As written in `privacy-impact-assessment.md` §9, next to the input box.

---

## 3. Intended use

| User | Intended use | Story |
|---|---|---|
| **Policyholder with a rejected claim** | Understand how disputes like theirs have been decided, and what the ombudsman paid attention to, before deciding whether to complain | `user-stories.md` §2 |
| **Family member or caregiver** | Understand why a claim was rejected and read comparable cases in plain language | §3 |
| **Advisor or consumer-help volunteer** | Find relevant precedents quickly for the person they are helping, and know where the tool is weak | §4 |
| **Reviewers of the project** (recruiters, researchers) | Inspect a reproducible example of calibrated, cited, abstaining GenAI | Model Card, Data Explorer |

**Conditions of intended use:** English text; health insurance; a claim that was rejected or partly paid; a person who will still read the policy, the rejection letter and the ombudsman's own guidance.

---

## 4. Unintended and out-of-scope uses

| Use | Why it is out | What the project does about it |
|---|---|---|
| **Legal advice**, or deciding whether to complain on the estimate alone | The model sees a short description, not the evidence; it can be wrong in either direction | Disclaimer; extended notice; no "you should" language anywhere; no drafting of complaints (`scope.md` §3.1) |
| **Drafting complaints, appeals or legal arguments** | Moves from describing to advising | Not built; V2-12 needs its own scope decision |
| **Insurers screening which complaints to fight or settle**, or which claims to reject | Turns a tool for policyholders into one used against them; trained on a biased sample of escalated cases | Stated here and in the README and model card; no API or hosted service in v1 |
| **Underwriting, pricing or claim decisions** | Not trained for it; an automated decision about someone's money | Out of scope; stated in the model card |
| **Ranking or judging named insurers** | Escalated complaints are a skewed sample of each insurer's claims (`fairness-analysis-plan.md` §4.2) | No per-insurer metrics are published |
| **Claims about ombudsman bias or consistency** | The data is a selected sample (`limitations.md` L1) and labels contain noise | Reports describe model behaviour, not ombudsman behaviour |
| **Other insurance lines** (motor, life, travel, property) | Different policy logic; no training data | `OFF_TOPIC` abstention |
| **Non-English input** | No training or evaluation data | `UNSUPPORTED_LANGUAGE` abstention |
| **Looking up or identifying people in past decisions** | Privacy | Anonymisation; no search by person; `privacy-impact-assessment.md` |
| **Hosting the app publicly as-is** | No rate limiting, no logging policy, user input sent to an LLM provider | v1 is local only; V2-08 lists the prerequisites |

---

## 5. Harm register

Harms to **users**. Data-subject privacy harms are in `privacy-impact-assessment.md` §6.

| ID | Harm | How it happens | Severity | Controls | Measured by |
|---|---|---|---|---|---|
| **H1** | **False discouragement**: the user drops a claim they would have won | Predicts `rejected` when the true outcome is any payment | **High** (money lost; time limits may pass) | Calibration (ECE ≤ 0.05); abstention; all three probabilities shown; abstain messages never call the claim weak; FD rate tracked per slice with a flag rule | FD rate, overall and per slice (`fairness-analysis-plan.md` §2) |
| **H2** | **False hope**: the user spends time and effort on a losing complaint | Predicts any payment when the true outcome is `rejected` | Medium | Same as H1; precedents with the opposite outcome stay visible | FH rate per slice |
| **H3** | **Over-reliance** on the number (automation bias) | A precise-looking percentage reads as a verdict | High | Probability shown as "about 7 in 10 similar cases"; rounded; disclaimer under the result; precedents shown before the explanation | Plain-language review (§7) |
| **H4** | **Misread probability** | "70%" read as "70% of the money" or "certain" | Medium | Natural-frequency wording; headline names the outcome, not a promise; tooltip explains what the number means | Plain-language review |
| **H5** | **Jurisdiction confusion** | Indian user reads a UK or Irish precedent as applying to them | Medium | Country shown on every precedent; jurisdiction note (§2.6); India-only metrics on the Model Card | R13 check: India metrics vs overall |
| **H6** | **Invented or wrong reasons** in the explanation | LLM states something no precedent says | High | Explanation grounded only in retrieved findings; NLI citation filter drops uncited sentences; 40-case audit | Citation coverage 100%; audit ≥ 90% |
| **H7** | **Explanation contradicts the estimate** | Explanation summarises precedents that went the other way | Medium | Header says it describes the similar decisions, not the model's reasoning; contradiction rate reported (error code E5) | E5 tally in PR 15 |
| **H8** | **Outdated precedent** | Rules or policy wording changed after the decision | Medium | Decision year on every card; temporal split; drift check by quarter | E1 by quarter |
| **H9** | **Distress** | Reading a "rejected" estimate about a family member's treatment | Medium | Neutral tone; no red/green win/lose colours; abstain wording never blames the user; pointers to where help is available | Plain-language review |
| **H10** | **Unequal quality** across groups of claims | Model is worse for small claims, public-sector insurers or Indian cases | Medium | Slice metrics with flag rules; flagged-slice note in the app (§2.5); finding written into `limitations.md` | Four flag rules |
| **H11** | **Exposure of the user's own details** | Description sent to the LLM provider | Medium | Privacy notice; advice to leave out identifiers; no storage | `privacy-impact-assessment.md` P-R7 |
| **H12** | **Unhelpful refusal** | Abstains on a common, clear-cut case | Low | Coverage ≥ 0.50 target; `LOW_CONFIDENCE` still shows precedents | Coverage and abstain rate per slice |

**Priority:** H1, H3 and H6 are the harms the design works hardest against. When two controls conflict, the one that reduces H1 wins (for example, abstaining more is preferred over showing a confident `rejected`).

---

## 6. Presentation rules (PR 17)

| Rule | Reason |
|---|---|
| Never use "you will", "you should", "your chances" or "guaranteed" | Avoids advice and promise framing (H3) |
| Say "past cases like yours", "similar decisions" | Keeps the claim about precedents, not the user's future |
| Show all three class probabilities, not just the winner | A 45 / 40 / 15 split reads differently from 90 / 5 / 5 (H3, H4) |
| No green for "upheld" or red for "rejected"; one neutral colour for all bars | Avoids a win/lose frame (H9) |
| Precedents appear **above** the explanation | Users see the evidence before the summary of it (H6) |
| Every precedent shows country, ombudsman, year, outcome | H5, H8; gap G1 |
| No result is shown without the disclaimer on screen | FR-19 |
| When `abstain` is true, no label or probability anywhere on the page, including hidden elements | FR-14 note |
| Model Card page states the abstain rate, India-only results and known failure modes | NFR-11 |
| No jargon in user-facing text: "upheld", "calibrated" and "precedent" each get a one-line tooltip | NFR-12 |

---

## 7. Plain-language review (NFR-12)

Before PR 17 merges:

1. Generate results for 10 fixture inputs covering every outcome and every abstention code.
2. Ask **two people who are not engineers** (for example, a family member who has dealt with a health claim) to read each screen and answer: *What is ClaimSense telling you? Would you complain to the ombudsman based on this alone?*
3. Record the answers in the PR description. If anyone reads a result as a promise or as advice ("it says I'll win"), the wording is changed and the review repeated.

---

## 8. Communicating this outside the app

| Place | Must include |
|---|---|
| README | The disclaimer; §3 intended use in two lines; §4 unintended uses as a short list; a link to this file |
| `MODEL_CARD.md` | Intended use, out-of-scope uses, harm register summary, abstain rate, link to `limitations.md` |
| Demo video or screenshots | The disclaimer visible in every frame that shows a result |
| Résumé and portfolio | Describe it as predicting ombudsman outcomes from public decisions; never as giving legal advice or "winning claims" |

---

## 9. Tests (PR 17)

| Test | Checks |
|---|---|
| `test_disclaimer_every_page` | Each of the four pages renders the exact FR-19 string |
| `test_disclaimer_on_abstain` | Each abstention screen renders the disclaimer |
| `test_text_constants` | All §2 strings come from `app/text.py`; no hard-coded duplicates in page files |
| `test_no_label_on_abstain` | Abstained results render no label or probability text |
| `test_banned_phrases` | No user-facing string contains "you will", "you should", "guarantee" or "your chances" |
| `test_precedent_shows_country` | Each precedent card renders country and ombudsman (gap G1) |
| `test_all_three_probabilities` | Non-abstained results show three bars that sum to 100% ± 1 |
| `test_flagged_slice_note` | Note appears for an input in a flagged slice and not otherwise |

---

*ClaimSense describes how similar past cases were decided. It is not legal advice; the ombudsman decides each case on its own facts.*
