<!--
  MODEL_CARD.md lifecycle
  - PR 11 (feat/lora-finetune): sections 1–3 and 5 filled with validation results (marked "val").
  - PR 12: calibration section (val), PR 16: abstention section (val operating point).
  - PR 18 (release/v1.0): all test numbers filled from reports/metrics.json; failure modes from
    reports/error-analysis.md; §9 short limitations copied from docs/responsible-ai/limitations.md §6.
  - The app's Model Card page renders this file. No ⟨…⟩ placeholder may remain at the v1.0 tag.
  - Follows the structure of Mitchell et al. (2019), "Model Cards for Model Reporting".
-->

# ClaimSense — Model Card

> A 3-class classifier that estimates how an insurance ombudsman is likely to rule on a rejected health-insurance claim, from a description of the facts, with calibrated probabilities and an abstention rule. It is one stage of the ClaimSense pipeline; precedent retrieval and cited explanations are described in §6.

> [!IMPORTANT]
> ClaimSense describes how similar past cases were decided. It is not legal advice; the ombudsman decides each case on its own facts.

---

## 1. Model details

| Item | Value |
|---|---|
| Name | ClaimSense outcome classifier |
| Version | `⟨1.0.0⟩` · run `⟨run_id⟩` |
| Developer | Diya Shrivastava (solo project) |
| Type | Sequence classification, 3 classes: `rejected`, `partially_upheld`, `upheld` |
| Base model | `answerdotai/ModernBERT-base` (~150 M parameters, Apache-2.0), revision `⟨hub commit⟩` ⟨or fallback actually shipped⟩ |
| Adaptation | LoRA (PEFT): r = ⟨16⟩, α = ⟨32⟩, dropout 0.1; classification head trained in full |
| Input | `facts_text`: complaint + insurer's position, anonymised; max 1,024 tokens, head 75% + tail 25% truncation |
| Output | Calibrated probability for each class; label = top class unless the case abstains |
| Calibrator | ⟨temperature scaling / isotonic⟩ fitted on 2024 validation data |
| Training data | Dataset `⟨v________⟩` — see [`DATA_CARD.md`](DATA_CARD.md) |
| Seeds | 13, 42, 2027; shipped seed ⟨…⟩ is the **median** by val macro-F1, not the best |
| Trained on | ⟨Kaggle T4 / Colab T4⟩, ⟨…⟩ GPU-hours total for the search |
| Released files | `models/lora-adapter/` (adapter + head + `meta.json`), `models/calibrator.pkl`, `models/thresholds.json` |
| Licence | Adapter and code: MIT. Base model: its own licence. Data: see [`DATA_SOURCES.md`](DATA_SOURCES.md) |
| R8 fallback used? | ⟨No / Yes — fine-tuning did not beat every baseline; shipped model is …⟩ |

---

## 2. Intended use

### Intended users and uses

| User | Use |
|---|---|
| Policyholder with a rejected health claim | See how similar disputes were decided before deciding whether to approach the ombudsman |
| Family member or caregiver | Understand the stated rejection reason in light of past decisions |
| Insurance advisor or consumer-help volunteer | Find relevant precedents quickly for the person they are helping |
| Researchers and students | Study how published ombudsman decisions on health claims were decided |

### Out of scope

- **Legal advice**, or any statement that a person will win or lose.
- Decisions **about** individuals by insurers, employers, lenders or anyone else.
- Ranking or scoring insurers.
- Non-health insurance, critical-illness or disability lump sums, delay-only or interest-only complaints.
- Non-English input; uploaded policies or letters (v1 reads only a typed description).
- Predicting **how much** will be paid or **how long** a complaint takes.

---

## 3. Factors

Performance is reported separately for these groups, because each could plausibly change how well the model works (plan: [`fairness-analysis-plan.md`](docs/evaluation/fairness-analysis-plan.md)).

| Factor | Groups | Why |
|---|---|---|
| **Country / ombudsman** | India · UK · Ireland | Different law, products and procedure; India is the primary user base |
| Rejection reason | Pre-existing disease, non-disclosure, waiting period, exclusion, medical necessity, documentation, sub-limit, other | Some reasons are decided on documents the model never sees |
| Insurer type (India) | Public · private · standalone health | Different claim practices |
| Claim size band | ⟨bands from config⟩ | Small claims may be decided differently |
| Decision quarter | 2025 Q1 … ⟨last⟩ | Drift after rule changes |

Slices with n < 30 report counts only; ECE only for n ≥ 100.

---

## 4. Metrics

| Metric | Why this one |
|---|---|
| **Macro-F1** (primary) | Weights the three outcomes equally, so ignoring the rare `partially_upheld` class is penalised |
| F1 per class | Shows whether the minority class is learned at all |
| PR-AUC, "any payment" (upheld + partial vs rejected) | The question most users care about; less affected by the upheld/partial label boundary |
| ECE, Brier score | Whether "70%" means 70% |
| Coverage, selective macro-F1, AURC | What abstention costs and buys |

All intervals are 95% bootstrap CIs over test records (paired bootstrap for model differences). Protocol, fixed before the test split was read: [`evaluation-protocol.md`](docs/evaluation/evaluation-protocol.md).

---

## 5. Evaluation results

Test split: decisions dated **2025-01-01 onward** (n = ⟨…⟩: India ⟨…⟩ · UK ⟨…⟩ · Ireland ⟨…⟩). Abstention **off** in this table so every model is scored on the same records.

### 5.1 Classification

| Model | Macro-F1 [95% CI] | F1 upheld | F1 partial | F1 rejected | PR-AUC any payment |
|---|---|---|---|---|---|
| B1 Majority | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| B3 TF-IDF + LR | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| B5 Zero-shot LLM | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| **ClaimSense** | **⟨…⟩** | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |

Validation, 3 seeds: macro-F1 ⟨mean ± sd⟩. Fine-tuned − B3 on test: ⟨Δ [CI]⟩. All five baselines: [`reports/evaluation-report.md`](reports/evaluation-report.md) §2.

### 5.2 By country (results for India first)

| Group | n | Macro-F1 [CI] | PR-AUC any payment | ECE |
|---|---|---|---|---|
| **India** | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| UK | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| Ireland | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| India, model trained **without** India | ⟨…⟩ | ⟨…⟩ | — | — |

India in training data: ⟨yes / no — R1 contingency applied⟩.

### 5.3 Drift

Macro-F1 by decision quarter: ⟨trend in one sentence⟩. Figure: `reports/figures/drift_by_quarter.png`.

### 5.4 Leakage check

Facts-only fine-tuned macro-F1 ⟨…⟩ vs findings-included ceiling (B3 on findings) ⟨…⟩: gap ⟨…⟩ (alarm if < 0.05). Leak probes: ⟨pass⟩.

---

## 6. Pipeline components around the classifier

| Component | Model | Key result (test) | Target |
|---|---|---|---|
| Precedent retrieval | `BAAI/bge-small-en-v1.5` + FAISS, filtered to earlier decisions | Reason match@5 ⟨…⟩ · earlier-only ⟨100%⟩ | ≥ 0.60 · 100% |
| Explanation | ⟨LLM provider / model / version⟩, grounded only in retrieved findings | Sentences with a valid cite ⟨100%⟩ | 100% |
| Citation checker | `cross-encoder/nli-deberta-v3-base` | Supported share of kept sentences ⟨…⟩ · checker–human agreement ⟨…⟩ | ≥ 0.90 · ≥ 0.90 |
| Whole `predict()` | Laptop CPU ⟨model⟩ | p50 ⟨…⟩ s · p95 ⟨…⟩ s | p95 ≤ 10 s |

The explanation summarises **precedents**; it is not an account of why the classifier chose its label, and it can describe precedents that went the other way.

---

## 7. Calibration

| Split | ECE [CI] before | ECE [CI] after | Brier [CI] after |
|---|---|---|---|
| Validation (cross-fitted) | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| **Test** | ⟨…⟩ | **⟨…⟩** | ⟨…⟩ |
| Test, India only | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |

**E4 (test ECE ≤ 0.05): ⟨✅ / ❌⟩.** Reliability diagrams: `reports/figures/reliability_val.png`, `reports/figures/reliability_test.png`.

Calibration is fitted on 2024 data and holds only for inputs like that data. It is not guaranteed for unusual cases, foreign-jurisdiction cases or user-written text.

---

## 8. Abstention

ClaimSense refuses to give an estimate when a wrong confident answer would be worse than none. Checked in this order; the first that fires is returned.

| Code | Fires when | What the user sees |
|---|---|---|
| `INPUT_TOO_SHORT` | Fewer than 80 characters | Message only |
| `UNSUPPORTED_LANGUAGE` | Not English | Message only |
| `OFF_TOPIC` | Fails the keyword gate or the in-scope classifier | Message only |
| `NO_PRECEDENTS` | Fewer than ⟨2⟩ earlier decisions above similarity ⟨…⟩ | Message only |
| `LOW_CONFIDENCE` | Top calibrated probability < τ = ⟨…⟩ | No outcome; similar past cases still shown |

τ was chosen on validation as the lowest value ≥ 0.50 with selective accuracy ≥ 0.75 and coverage ≥ 0.50 ([`abstention-policy.md`](docs/modelling/abstention-policy.md)).

| Test result | All | India | UK | Ireland |
|---|---|---|---|---|
| Coverage at τ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| **Abstain rate** | **⟨…⟩** | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| Selective macro-F1 [CI] | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| Full-coverage macro-F1 | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| Abstain: `OFF_TOPIC` / `NO_PRECEDENTS` / `LOW_CONFIDENCE` | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| Off-topic recall (fixtures) | ⟨…⟩ | — | — | — |

AURC ⟨…⟩. Figure: `reports/figures/coverage_accuracy_test.png`.

---

## 9. Failure modes

From the 50-case error analysis ([`reports/error-analysis.md`](reports/error-analysis.md)); codes from [`error-taxonomy.md`](docs/evaluation/error-taxonomy.md). Every code with ≥ 3 cases is listed.

| Failure mode | Code | Cases (of 50) | Example pattern | Mitigation in v1 |
|---|---|---|---|---|
| Deciding fact not in the facts (e.g. date of first diagnosis, proposal-form disclosure) | I | ⟨…⟩ | ⟨…⟩ | Low confidence → abstain; stated as limitation L6 |
| Upheld vs partially upheld confusion | ⟨M⟩ | ⟨…⟩ | ⟨…⟩ | All three probabilities shown |
| Label error in source mapping | D1 | ⟨…⟩ | ⟨…⟩ | Label audit reported |
| Rule or practice change since training | M5 | ⟨…⟩ | ⟨…⟩ | Decision year shown on precedents |
| Foreign-jurisdiction pattern applied to an Indian case | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | Jurisdiction note when most precedents are foreign |
| ⟨other code ≥ 3 cases⟩ | | | | |

### Flagged slices

⟨One row per slice that met a flag rule, e.g. higher false-discouragement rate for small claims, with FD rate [CI] and likely cause — or: "No slice met a flag rule at the test-set sizes available; small slices were not tested and may still differ."⟩

### Explanation failures (40-case audit)

Misattribution ⟨…⟩ · query misstatement ⟨0⟩ · overgeneralisation ⟨0⟩ · **advice or guarantee sentences ⟨0⟩** · explanation contradicting the predicted label ⟨…⟩ · empty explanations ⟨…⟩ / 40.

---

## 10. Limitations

> ClaimSense learned from health-insurance disputes that reached ombudsmen in India, the UK and Ireland and ended in a published decision; it knows nothing about claims that were settled or never escalated. UK and Irish rules differ from India's, and results for Indian cases are reported separately: ⟨India macro-F1⟩ vs ⟨overall macro-F1⟩. Outcomes in Indian awards were labelled by rules and are about ⟨label accuracy⟩ correct. The model was trained on decisions up to 2023 and tested on 2025 onward; rules may have changed since. It was trained on case summaries written by the ombudsman, not by users, so real-world accuracy is likely lower than reported. It cannot see your documents, and it declines to answer about ⟨100 − coverage⟩% of the time.

All fifteen limitations: [`docs/responsible-ai/limitations.md`](docs/responsible-ai/limitations.md).

---

## 11. Ethical considerations

| Concern | How it is handled |
|---|---|
| People may treat an estimate as advice | Disclaimer on every page; no advice or guarantee wording (audited, target 0); abstention when unsure |
| False discouragement: a "rejected" estimate stops someone with a good case | False-discouragement rate reported per slice; precedents and all probabilities always shown |
| Personal data in source decisions | Removed before processing; raw files never leave the author's laptop; 0 PII hits required on audit ([`privacy-impact-assessment.md`](docs/responsible-ai/privacy-impact-assessment.md)) |
| Unfair performance across groups | Slices by country, reason, insurer type, claim size, reported with CIs |
| Misuse against policyholders (e.g. insurer triage) | Stated as out of scope; data card forbids decisions about individuals |
| User input sent to an LLM | Only for explanations, only after the topic check; nothing stored by default ([`responsible-use.md`](docs/responsible-ai/responsible-use.md)) |

---

## 12. How to use

```python
from claimsense import predict

r = predict("Describe what happened, what the policy says and why the claim was rejected ...")
r.abstained, r.abstain_code, r.label, r.probabilities, r.precedents, r.explanation
```

`predict()` refuses to run if the adapter, calibrator, thresholds and index were built from different dataset versions (`ArtifactMismatchError`). Interface: [`pipeline-interface.md`](docs/architecture/pipeline-interface.md).

---

## 13. Change log for this card

| Date | Version | Change |
|---|---|---|
| ⟨PR 11 date⟩ | 0.11.0 | Model details and validation results |
| ⟨PR 12 date⟩ | 0.12.0 | Calibration (validation) |
| ⟨PR 16 date⟩ | 0.16.0 | Abstention operating point |
| ⟨PR 18 date⟩ | 1.0.0 | Test results, failure modes, limitations |

---

<sub>ClaimSense describes how similar past cases were decided. It is not legal advice; the ombudsman decides each case on its own facts.</sub>
