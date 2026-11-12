# ClaimSense — Project Overview

> Predicts how an insurance ombudsman is likely to rule on a rejected health-insurance claim, with a calibrated probability, cited precedents and a plain-language explanation.

**Type:** Solo GenAI project · **Scope:** 18 PRs · **Author:** Diya Shrivastava
**Not in scope:** agents, MCP, legal advice

---

## Problem

Policyholders rarely understand their health-insurance policies, so when a claim is rejected they cannot tell whether the rejection is fair or worth contesting.

- Indian health insurers disallowed **₹15,100 crore** of claims in FY24, **12.9%** of all claims filed (IRDAI Annual Report 2023-24).
- Health-insurance complaints rose **41%** to **1,37,361** in FY25, driven mainly by claim disputes, delays and partial settlements (IRDAI Annual Report 2024-25).
- The answers already exist in public: insurance ombudsmen publish thousands of decisions on exactly these disputes. They are long, scattered PDFs that no ordinary policyholder will read.

## Solution

ClaimSense turns those past ombudsman decisions into a usable signal for a new dispute.

1. **Input:** the user describes their claim: what happened, what the policy says, and why the insurer rejected it.
2. **Predict:** a LoRA fine-tuned model estimates the likely outcome (*Upheld / Partially upheld / Rejected*) as a **calibrated probability**.
3. **Retrieve:** the most similar past decisions, dated earlier than the case, are shown as **precedents**.
4. **Explain:** an LLM writes a short explanation grounded only in those precedents. Every sentence must cite one; uncited sentences are dropped.
5. **Abstain:** when confidence is low or the case is out of scope, it says so instead of guessing.

**Core design rule:** the model sees only the *facts* of each case, never the ombudsman's findings, so it cannot learn by reading the answer.

## Data

Real, public ombudsman decisions with real outcomes:

| Source | Country | Use |
|---|---|---|
| Council for Insurance Ombudsmen (CIOINS) awards | India | Primary target domain |
| Financial Ombudsman Service (FOS) decisions | UK | Large training volume |
| Financial Services and Pensions Ombudsman (FSPO) decisions | Ireland | Structured outcome labels |

All personal details are anonymised before processing. Only derived data is published, never raw PDFs.

## Users

| User | Need |
|---|---|
| **Policyholder with a rejected claim** | "Is it worth taking my case to the ombudsman?" |
| **Family member or caregiver** handling a claim | Understand the rejection reason and how similar cases went |
| **Insurance advisor or consumer-help volunteer** | Quickly find relevant precedents for the person they are helping |

## Goals

**Product goals**
- Beat simple baselines (TF-IDF, rules, zero-shot LLM) on a **temporal hold-out** of the newest decisions.
- Produce **calibrated** probabilities (target ECE ≤ 0.05).
- Every explanation sentence is backed by a cited precedent.
- Report honestly where the model fails (by country, rejection reason, insurer type, claim size).

**Learning and career goals**
- Add **LoRA/PEFT fine-tuning**, legal-text dataset construction, PII anonymisation and faithfulness checking to my skill set.
- Ship a reproducible, tested project (CI, model card, data card) that a fresh clone can rerun to the reported metrics.

## Success criteria

- [ ] Frozen, anonymised, deduplicated dataset with a temporal split
- [ ] Fine-tuned model beats every baseline, with confidence intervals
- [ ] Calibration, retrieval and explanation-faithfulness results in one evaluation report
- [ ] Streamlit app with Predict, Precedent Explorer and Model Card pages, a disclaimer on every page
- [ ] README, model card and data card; tagged v1.0

---

*ClaimSense describes how similar past cases were decided. It is not legal advice; the ombudsman decides each case on its own facts.*
