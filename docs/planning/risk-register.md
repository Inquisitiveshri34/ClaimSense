# ClaimSense — Risk Register

> Fifteen risks (R1–R15) from the project description, each with a trigger, a mitigation, the PR where it is checked, and a live **status**.

**Author:** Diya Shrivastava · **Source:** `05-project-description.md` §10 · **Gates:** `planning/roadmap.md` §4 · **Contingencies:** `scope.md` §5

---

## 1. Status legend

| Status | Meaning |
|---|---|
| **Open** | Identified; its checkpoint PR has not been reached yet |
| **Monitoring** | Checkpoint reached; trigger not hit; still watched in later PRs |
| **Triggered** | Trigger hit; mitigation or contingency is being applied |
| **Mitigated** | Mitigation applied and verified; residual risk accepted |
| **Closed** | No longer applicable (e.g. the phase it affects is finished) |
| **Design control** | Handled by a permanent design feature, verified at release |

Likelihood and impact: **Low / Medium / High**. Status as of project start (no PRs merged).

---

## 2. Register

| # | Risk | Likelihood | Impact | Mitigation | Trigger / owner check | Check at PR | Status |
|---|---|---|---|---|---|---|---|
| R1 | Too few usable Indian health awards | Medium | High | Train on UK + Ireland; India becomes the out-of-distribution test | < 800 usable awards after PR 5 | 3, 5 | Open |
| R2 | Terms of use forbid bulk collection or redistribution | Medium | High | Request permission; keep data local; publish code, statistics and weights only | PR 2 checklist | 2 | Open |
| R3 | Findings leak into the input | Medium | High | Section segmenter, leak-probe tests, facts-vs-findings gap check | Leak tests in CI; suspiciously high accuracy | 6, 14 | Open |
| R4 | Segmenter fails on varied office layouts | High | Medium | Per-source and per-office rules; hand-check sample; drop unparseable files with a logged count | < 95% on 50-doc check | 5 | Open |
| R5 | PII survives anonymisation | Medium | High | Presidio + Indian patterns + manual sample + automated scan; never publish raw text | Any hit in the 100-doc sample | 6, 18 | Open |
| R6 | Label noise from free-text Indian awards | Medium | Medium | Rule-based mapping, hand audit of 100 labels, report label accuracy | Audit accuracy < 95% | 6 | Open |
| R7 | Class imbalance (e.g. few partial upholds) | High | Medium | Macro-F1, class weights, binary view reported alongside | Any class < 10% of data | 7, 8 | Open |
| R8 | Fine-tuning does not beat simple baselines | Medium | Medium | Report it honestly; analyse why; keep the strongest model | PR 11 validation results | 11 | Open |
| R9 | Free GPU limits or session timeouts | Medium | Low | Small model, LoRA, gradient accumulation, frequent checkpoints | Repeated interrupted runs | 11 | Open |
| R10 | LLM explanations invent reasons | Medium | High | Retrieval-only grounding, NLI citation filter, manual audit | Audit agreement < 90% | 13, 15 | Open |
| R11 | LLM API rate limits or cost | Low | Low | Cache outputs; small free-tier models; batch evaluation | API errors during PR 13–15 | 10, 13–15 | Open |
| R12 | Users treat predictions as advice | Medium | High | Disclaimer on every page, abstention, model card limits | — (design control) | 16, 17, 18 | Design control |
| R13 | Jurisdiction mismatch misleads Indian users | Medium | Medium | Show precedent country; report India-only metrics separately | India metrics far below overall | 14, 17 | Open |
| R14 | Source sites change structure mid-project | Low | Medium | Store raw files once; collectors have tests against saved sample pages | Collector tests fail | 3, 4 | Open |
| R15 | Scope creep (agents, MCP, extra features) | Medium | Medium | Out-of-scope list fixed; extras go to a v2 backlog | New feature not in the 18 PRs | Every PR | Open |

---

## 3. Heat map

| Likelihood ↓ / Impact → | Low | Medium | High |
|---|---|---|---|
| **High** | | R4, R7 | |
| **Medium** | R9 | R6, R8, R13, R15 | R1, R2, R3, R5, R10, R12 |
| **Low** | R11 | R14 | |

The **Medium / High** cell holds six risks; four of them (R2, R3, R5, R1) are decided in the Data phase, which is why `planning/roadmap.md` puts three of its five gates before PR 7.

---

## 4. Spec links

| Risk | Where the mitigation is specified |
|---|---|
| R1 | `scope.md` §5, `data/collection-runbook.md` |
| R2 | `data/terms-of-use-audit.md` |
| R3 | `leakage-contract.md`, `data/segmentation-rules.md` |
| R4 | `data/segmentation-rules.md`, `data/manual-audit-protocol.md` |
| R5 | `data/anonymisation-spec.md`, `responsible-ai/privacy-impact-assessment.md` |
| R6 | `data/labelling-guide.md`, `data/manual-audit-protocol.md` |
| R7 | `modelling/baselines.md`, `evaluation-protocol.md` |
| R8 | `modelling/finetuning-spec.md`, `modelling/experiment-log.md` |
| R9 | `modelling/finetuning-spec.md` |
| R10 | `modelling/citation-checking.md`, `faithfulness-rubric.md` |
| R11 | `modelling/prompt-spec.md` |
| R12 | `modelling/abstention-policy.md`, `responsible-ai/responsible-use.md` |
| R13 | `evaluation-protocol.md`, `fairness-analysis-plan.md` |
| R14 | `data/collection-runbook.md` |
| R15 | `scope.md` §6, `planning/backlog-v2.md` |

---

## 5. Review routine

- **At every PR merge:** update the *Status* of each risk whose *Check at PR* includes that PR, and add a row to the change log.
- **At each phase exit:** move risks whose phase has ended and whose trigger was never hit to **Closed** or **Mitigated**.
- **When a trigger fires:** set **Triggered**, record the contingency taken, and update `planning/roadmap.md` if the timeline moves.
- **New risks:** add as R16 onward with the same columns; do not renumber existing risks.

---

## 6. Change log

| Date | PR | Risk | Status change | Note |
|---|---|---|---|---|
| — | — | All | — → Open (R12 → Design control) | Register created from `05-project-description.md` §10 |
