# ClaimSense — User Guide

> How to use the ClaimSense app: starting it, describing a rejected health-insurance claim so ClaimSense can compare it with past decisions, and reading what comes back — the estimate, the similar past cases, the explanation, and the messages ClaimSense shows when it will not give an estimate. Written for the people the app is for, most of whom are not engineers.

**Author:** Diya Shrivastava · **Owning PR:** 17 · **Status:** Planned

**Related:** FR-14, FR-17, FR-18, FR-19, NFR-11, NFR-12, `../responsible-ai/responsible-use.md` (all fixed wording), `../pipeline-interface.md` §2–§3, `../modelling/abstention-policy.md` §7, `../responsible-ai/privacy-impact-assessment.md` §9, `../responsible-ai/limitations.md`, `../user-stories.md`, `setup.md`.

> **ClaimSense describes how similar past cases were decided. It is not legal advice; the ombudsman decides each case on its own facts.**

---

## 1. What ClaimSense does, in one minute

When a health insurer rejects a claim, you can usually complain to an **insurance ombudsman**: an independent office that decides disputes between people and insurers. Ombudsmen in India, the UK and Ireland publish their decisions.

ClaimSense has read thousands of those published decisions. When you describe your situation, it:

1. finds the **past decisions most like yours**, and shows them to you;
2. estimates **how cases like yours were usually decided**: upheld (the insurer had to pay), partly upheld (the insurer had to pay part), or rejected (the insurer's decision stood);
3. writes a short **explanation of what the ombudsman focused on** in those past cases, with each sentence linked to the case it comes from.

It does **not** read your policy, letters or medical records. It does **not** tell you what to do. It describes the past; the ombudsman decides your case.

---

## 2. Starting the app

The app runs on your own computer. Nothing is hosted online in v1.

```bash
cd claimsense
make app
```

This runs `streamlit run src/claimsense/app/Home.py` and opens `http://localhost:8501` in your browser. The first start takes up to a minute while the models load; after that each estimate takes a few seconds.

First-time installation: `setup.md`. The app needs the trained models in `models/` and the precedent index in `index/precedents/`; without them it shows a setup message instead of the Predict page.

### The four pages

| Page | What it is for |
|---|---|
| **Predict** | Describe your claim and get an estimate, similar cases and an explanation |
| **Precedent Explorer** | Browse past decisions yourself, filtered by the insurer's reason, insurer type and year |
| **Model Card** | How accurate ClaimSense is, how often it declines to answer, and where it is weak |
| **Data Explorer** | What decisions ClaimSense learned from: how many, from where, from which years |

The disclaimer is at the top of every page.

---

## 3. Describing your claim

### 3.1 What to include

ClaimSense compares your description with the part of past decisions written **before** the ombudsman decided: what the person said happened and what the insurer said. So the best descriptions cover the same three things:

| Include | Examples |
|---|---|
| **What happened** — the treatment and when | "Admitted to hospital for 3 days with dengue in March 2025." "Knee replacement surgery." "Day-care cataract procedure." |
| **The policy** — what kind, and how long you had it | "Family floater policy, started 14 months before the admission." "Group policy through my employer." "Renewed every year since 2019." |
| **Why the insurer rejected the claim** — in their words if you have them | "They said I did not disclose diabetes." "They said the treatment was not medically necessary." "They said it falls under the 2-year waiting period." "They said documents were missing." |

Helpful extras, if they apply:

- the amount claimed and how much (if any) was paid;
- what you told the insurer when you bought the policy;
- dates: policy start, diagnosis, admission, rejection;
- anything you have already done (complained to the insurer's grievance officer, and their reply).

### 3.2 What to leave out

Your description is sent to an online AI service to write the explanation (§3.5), so **do not include**:

- names (yours, family members', doctors');
- policy, claim or membership numbers;
- phone numbers, email or home addresses;
- ID numbers of any kind.

ClaimSense does not need any of these. "My father" works as well as his name.

### 3.3 A weak and a strong description

| Weak (likely to get "please add more detail") | Strong |
|---|---|
| "My claim got rejected. Is that allowed?" | "My mother was admitted for 4 days for a gallbladder surgery in January 2025. Her individual mediclaim policy started in 2021 and has been renewed every year. The insurer rejected the ₹1.2 lakh claim saying she had gallstones before the policy started and did not disclose it. Her first ultrasound showing gallstones was in 2024, three years after the policy began. We have the report." |

The strong version says what was treated, how long the policy had run, exactly why the insurer refused, and the fact that contradicts the insurer's reason. That is what past cases turn on.

### 3.4 The other boxes

| Box | Why it is there | Required? |
|---|---|---|
| **Country** (India, UK, Ireland) | Shown next to the result so you can see when the closest past cases come from a different country than yours. It does not change the estimate | Yes; India is preselected |
| **Claim amount band** | Lets ClaimSense warn you if it has been less accurate for claims of that size | No |

### 3.5 Privacy notice (shown next to the input box)

What happens to what you type:

- It is **not saved** by ClaimSense: not to a file, not to a log.
- To write the explanation, your description and the similar past cases are **sent to an AI provider** (Groq or Gemini, whichever this installation uses). That provider's own terms apply.
- If you would rather nothing leaves your computer, tick **"Skip explanation"**: you still get the estimate and the similar cases, and no text is sent anywhere.

Full detail: `privacy-impact-assessment.md` §9.

---

## 4. Reading the result

A full result has five parts, in this order.

### 4.1 The headline

> In past cases like yours, the ombudsman most often **upheld the complaint**.

This names the outcome that was **most common among cases like yours**. It is not a prediction of your result and not a promise.

| Word | What the ombudsman did |
|---|---|
| **Upheld** | Told the insurer to pay the claim, in full or substantially |
| **Partly upheld** | Told the insurer to pay part of the claim |
| **Rejected** | Agreed with the insurer; nothing more to pay |

### 4.2 The estimate

> ClaimSense estimates about **7 in 10** similar cases ended this way.

Below it, three bars show the estimate for **all three** outcomes, for example:

```text
Upheld          ███████░░░  about 7 in 10
Partly upheld   ██░░░░░░░░  about 2 in 10
Rejected        █░░░░░░░░░  about 1 in 10
```

How to read it:

- **"7 in 10" means**: among past cases where ClaimSense gave this kind of estimate, about 7 in every 10 really ended this way. ClaimSense is tested to check that its numbers mean this (`calibration.md`). Hover over the number to see the exact figure.
- **It does not mean** you will get 70% of your money, or that you are 70% likely to win. Your case has facts ClaimSense cannot see.
- **Look at all three bars.** "5 in 10 / 4 in 10 / 1 in 10" is a close call; "9 in 10 / 1 in 10 / 0 in 10" is a clearer pattern. Both have the same headline.
- All bars are the same colour on purpose: no outcome is shown as "good" or "bad".

### 4.3 Similar past cases

Each card shows one earlier decision:

| On the card | What it tells you |
|---|---|
| **Country and ombudsman** (e.g. India · Insurance Ombudsman) | Rules differ between countries; an Indian decision is the most relevant to an Indian policy |
| **Year** | Older decisions may reflect older rules or policy wording |
| **Outcome** | How that case was decided |
| **Insurer's reason** | Why that insurer rejected the claim (non-disclosure, waiting period, exclusion, not medically necessary, documentation, other) |
| **Similarity** | How close that case's facts are to your description |
| **What the ombudsman found** | A short extract of the ombudsman's reasoning (names removed) |

Some similar cases may have gone the other way from the headline. That is normal and useful: read them to see what made the difference.

Only decisions **published before today** are shown.

If most of the cases shown are from a different country than the one you selected, you will see:

> Most of the closest past cases are from the UK, where the rules and policies differ from India's.

### 4.4 What the similar decisions said

A few plain-language sentences about what the ombudsman paid attention to in those cases, each ending with the case or cases it comes from, for example:

> In similar cases, the ombudsman asked whether the condition was diagnosed before the policy started. **[Case 1, Case 3]**

Click a case reference to jump to its card. Every sentence has been checked automatically against the case it cites, and sentences that the case does not support are removed before you see them (`citation-checking.md`). So:

- the explanation **describes past cases**; it is not ClaimSense's reasoning about your case, and it is not advice;
- it may be **shorter than expected**, or replaced with "No explanation could be supported by the precedents.", when nothing could be checked;
- if the AI service is unavailable you will see "The explanation is unavailable right now. The estimate and similar cases above are unaffected."

### 4.5 Notes and the disclaimer

- **Extra-caution note**: if ClaimSense has been less accurate on past cases from your country or with claims of your size, it says so under the estimate.
- **Disclaimer**: repeated directly under the result.
- **Extended notice** (under the disclaimer): ClaimSense cannot see your documents; the ombudsman will. Complaint schemes have time limits and usually require you to complain to the insurer first, so check the rules early.

---

## 5. When ClaimSense will not give an estimate

Sometimes ClaimSense declines. **This is about ClaimSense's limits, not about how strong your claim is.**

| Message you see | What it means | What you can do |
|---|---|---|
| "Please add more detail: what was treated, what the policy says, and the reason the insurer gave for rejecting the claim." | The description was too short to compare | Add the three things in §3.1 |
| "ClaimSense currently understands English only." | The description was not detected as English | Write it in English |
| "This doesn't look like a rejected health-insurance claim, which is the only kind of case ClaimSense has learned from." | The text looks like a motor, travel, life or home claim, a general question, or something unrelated | If it **is** a health claim, mention the treatment and the rejection clearly. If it is another kind of insurance, ClaimSense cannot help |
| "ClaimSense hasn't seen enough past decisions like this one to give an estimate." | Too few earlier decisions are close enough to compare | Nothing is wrong with your description; your situation is rare in the published decisions |
| "Similar past cases went different ways, so ClaimSense won't give an estimate. The closest cases are shown below so you can read how they were decided." | ClaimSense found similar cases, but they do not point clearly one way | Read the cases shown: what differs between the ones that were upheld and the ones that were not? |

ClaimSense prefers saying "can't tell" to showing a confident number that might be wrong (`abstention-policy.md`).

---

## 6. The other pages

### 6.1 Precedent Explorer

Browse past decisions directly, without describing a claim.

| Filter | Values |
|---|---|
| Insurer's reason | Non-disclosure, waiting period, exclusion, not medically necessary, documentation, other |
| Insurer type | Public sector, private, standalone health |
| Year | Range slider |
| Country | India, UK, Ireland |
| Outcome | Upheld, partly upheld, rejected |

Useful for advisors and volunteers who want to read how a type of dispute is usually decided. Names and identifying details are removed from every extract. There is no search by person.

### 6.2 Model Card

How well ClaimSense works, in plain words and in numbers: overall accuracy, results for Indian cases on their own, how well the "7 in 10" numbers hold up, how often each "won't estimate" message appears, known weak spots, and what ClaimSense should not be used for. Read this before relying on any estimate.

### 6.3 Data Explorer

Where the decisions came from: how many from each ombudsman, from which years, how outcomes are split, and which kinds of rejection are common. It shows counts and charts only, never full decision text.

---

## 7. Good and bad uses

| Good use | Not what ClaimSense is for |
|---|---|
| Understanding how disputes like yours have gone before | Deciding whether to complain on the estimate alone |
| Finding out what the ombudsman pays attention to (dates of diagnosis, what was disclosed, waiting-period wording) | Legal advice, or drafting a complaint or appeal |
| Preparing questions for the insurer, the ombudsman's office or a consumer-help organisation | Judging or ranking named insurers |
| Reading real past decisions in plain language | Motor, life, travel, property or other non-health claims |
| Helping someone else understand their situation | Looking up or identifying people in past decisions |

If you are unsure what to do, you can contact the **Insurance Ombudsman**, your insurer's **grievance officer**, or a **consumer-help organisation**.

---

## 8. Questions

| Question | Answer |
|---|---|
| Will I win if it says "upheld"? | Not necessarily. It says how similar **past** cases went. The ombudsman decides your case on its own facts and documents |
| Why is the estimate different when I change a few words? | The comparison works on what you describe. Adding a key fact (a date, the insurer's exact reason) can change which cases look similar. That is expected; describe your situation as accurately as you can, not in the way that gives the answer you hope for |
| Why are some cases from the UK or Ireland? | ClaimSense learned from all three countries. Each card shows the country so you can give more weight to decisions from yours |
| Why does it sometimes refuse? | See §5. It refuses when it cannot compare your case reliably, rather than guess |
| Does it keep what I type? | No (§3.5). The text is sent to the AI provider only to write the explanation, and only if you have not ticked "Skip explanation" |
| How recent are the decisions? | See the Data Explorer. v1 includes decisions up to its build date; later decisions are not included |
| Can I use it for someone else? | Yes. Leave out their name and other identifying details |

---

## 9. For developers: the same result in Python

The app calls one function. Its full contract is in `pipeline-interface.md`.

```python
from claimsense.pipeline import predict

r = predict(
    "Admitted for 3 days with dengue. Policy started 14 months ago. "
    "Insurer rejected the ₹85,000 claim saying I did not disclose diabetes, "
    "but I was diagnosed only after the policy began.",
    explain=False,          # skip the LLM call
)

if r.abstain:
    print(r.abstain_code)                       # e.g. "LOW_CONFIDENCE"
else:
    print(r.label, round(r.probability, 2))     # e.g. "upheld" 0.68
    print(r.class_probabilities)
for p in r.precedents:
    print(p.country, p.decision_date.year, p.label, round(p.similarity, 2))
```

Values are illustrative only.

---

*ClaimSense describes how similar past cases were decided. It is not legal advice; the ombudsman decides each case on its own facts.*
