# ClaimSense — Leak-Probe Tests

> What each leak-probe test asserts, why it exists, how its matching works, what makes it fail, and what to do when it does. These tests are how the leakage contract becomes something CI can prove: if any of them is red, a reported accuracy may mean the model read the answer rather than predicted it.

**Author:** Diya Shrivastava · **Owning PR:** 6 (L1, L2 probes and the harness) · 7 (L3, L4) · 12 (val-only calibrator case) · 13 (L5) · **Status:** Planned

**Related:** `leakage-contract.md` (the rules these tests enforce), `testing/test-strategy.md` §4–§6, `testing/test-fixtures.md` §6, `data/segmentation-rules.md` §5, `data/dataset-versioning.md` §6, `modelling/retrieval-design.md`, NFR-01, FR-08, FR-09, FR-12, FR-15, risk R3.

---

## 1. Overview

| # | Test file | Leak path | Asserts (one line) | Hard fail? | Added in PR |
|---|---|---|---|---|---|
| 1 | `test_sentence_probe.py` | L1 | No findings/award sentence appears in the same document's `facts_text` | ✅ | 6 |
| 2 | `test_ngram_probe.py` | L1 | No 13-gram shared between `facts_text` and findings + award, outside the policy-wording allowlist | ✅ | 6 |
| 3 | `test_marker_probe.py` | L1 | No findings/award marker string inside `facts_text` | ✅ | 6 |
| 4 | `test_lexicon_rate.py` | L2 | Outcome-word rate is computed per source × label and logged; `lexicon_hits` column is correct | Schema only | 6 |
| 5 | `test_input_columns.py` | L1 (code path) | Model-input builders read only `facts_text`; `findings_text` and labels never enter features | ✅ | 6 |
| 6 | `test_temporal_split.py` | L3 | Every record sits in the date range of its split; calibrator and thresholds use val indices only | ✅ | 7 (val-only case: 12) |
| 7 | `test_cross_split_dedup.py` | L4 | No pair across train/val/test is above the MinHash threshold; survivors are the earliest copies | ✅ | 7 |
| 8 | `test_retrieval_dates.py` | L5 | Every retrieved precedent is dated strictly before `before`; the query document is never returned | ✅ | 13 |

Test 5 is not in `leakage-contract.md` §6 yet: it is the only probe that guards **code** rather than **data**. The contract's layout should be updated to include it.

All probes run in **fixture mode** in CI on every PR (from the PR that adds them) and in **dataset mode** locally with `make test-data` (`testing/test-strategy.md` §4).

---

## 2. Shared harness — `tests/leak/_probe.py`

### 2.1 Two modes

| Mode | Records come from | Triggered by | Output |
|---|---|---|---|
| Fixture | `tests/fixtures/leak/*.jsonl` (clean + planted) | Default `pytest` run | Normal pytest pass/fail |
| Dataset | `data/interim/segments/` (L1 needs findings and award, which `data/processed/` does not keep) and `data/processed/v<hash>/` | `-m local_data` | pytest result + `reports/leak/leak_probe_report.csv` and `leak_probe_summary.txt` (local, git-ignored) |

L1 probes in dataset mode join the scrubbed `facts_text` from the processed set with the segment JSON for the same `doc_id`, after running both through the same anonymiser, so tokens line up.

### 2.2 Normalisation (applied to both sides before any comparison)

1. Unicode NFKC; straighten quotes and dashes.
2. Lowercase.
3. Collapse anonymiser indices: `[PERSON_2]` → `[PERSON]`, `[AGE_40-49]` → `[AGE]`, so a token number difference cannot hide a match.
4. Replace digits with `0` (amounts and dates are rewritten by the anonymiser at different points; the words around them are what matter).
5. Strip punctuation except sentence terminators; collapse whitespace.
6. Tokenise on whitespace.

The same `normalise()` function is used by all L1 probes and has its own unit tests.

### 2.3 Failure report format

Every hard failure prints one line per hit, never the full document:

```text
LEAK L1/sentence  doc=cioins-2023-05-AHD-0056  section=findings  facts_offset=1412  match="i am satisfied that the condition was not diagnosed before inception"  rule=cioins/ahmedabad/v2
```

The match is capped at 120 characters and is already anonymised. `rule` is the segmenter's `marker_rule`, so the fix can be traced to a rule version.

### 2.4 Configuration read from `config.yaml`

```yaml
leak:
  sentence_min_tokens: 6        # shorter sentences are left to the n-gram, marker and lexicon checks
  ngram_n: 13
  policy_allowlist_file: config/policy_wording_allowlist.txt
  quote_exempt: true            # spans inside quotation marks are allowlist candidates (see §4.2)
  max_report_hits: 200
dedup:
  jaccard_threshold: 0.8        # tuned in audit A4
  shingle_size: 5
  num_perm: 128
split:
  train_end: 2023-12-31
  val_end: 2024-12-31
```

---

## 3. Planted-violation self-tests (every probe)

A probe that never fails proves nothing. Each test file contains **two kinds of case**:

| Case | Fixture | Expected |
|---|---|---|
| Clean | Records known to be correctly segmented | Probe passes |
| Planted | The same records with one violation inserted | Probe **fails**, and reports the planted `doc_id` and offset |

Planted cases are run inside the test with `pytest.raises(LeakFound)` (or the equivalent assertion on the returned hit list), so CI is green only when the probe **catches** them. If someone weakens a probe (raises `ngram_n` to 50, breaks normalisation), the planted case stops being caught and the test goes red.

The planted fixtures are listed in `testing/test-fixtures.md` §6.

---

## 4. Probes in detail

### 4.1 `test_sentence_probe.py` — L1

**Asserts:** for every document, no normalised sentence of `findings` or `award` with ≥ `sentence_min_tokens` tokens is a substring of normalised `facts_text`.

**Why:** the most common segmentation failure is a whole sentence landing on the wrong side of a boundary: a missed heading, an ombudsman remark inside the facts, a FOS provisional decision quoted in "What happened". A whole-sentence match is the strongest evidence of leakage and the easiest to explain in a PR.

**How:** sentence split with a rule-based splitter (abbreviation list includes `Dr.`, `No.`, `Rs.`, `i.e.`, `viz.`), then substring search after §2.2 normalisation.

**Planted cases:**
- An award sentence ("The complaint is allowed and the insurer is directed to pay…") appended to `complaint`.
- A findings sentence with different anonymiser indices and amounts than the original (must still match after normalisation).
- A FOS-style quoted provisional finding inside "What happened".

**Not a failure:** a sentence of 5 tokens or fewer ("The complaint is upheld."). Those are caught by the marker and lexicon checks instead; a minimum length avoids false hits on generic sentences like "The policy was renewed."

**On failure:** look at `rule` in the report. Tighten the marker rule (new version, `segmentation-rules.md` §4) or drop the document. Never edit the text by hand (`leakage-contract.md` §2 edge cases).

### 4.2 `test_ngram_probe.py` — L1

**Asserts:** no `ngram_n`-token sequence (default 13) appears in both `facts_text` and `findings + award` of the same document, unless the shared span is on the policy-wording allowlist.

**Why:** leaks are often partial: a paraphrased or truncated finding, or two sentences merged by bad PDF extraction. A long shared n-gram catches these when the sentence probe does not. Thirteen tokens is long enough that ordinary phrasing ("the insurer rejected the claim on the ground that") rarely reaches it by chance.

**Allowlist:** both parties and the ombudsman quote the same policy clauses and exclusion wording. A shared span is exempt when it is
1. inside quotation marks in **both** sections (if `quote_exempt`), **or**
2. a substring of an entry in `config/policy_wording_allowlist.txt` (standard exclusion and waiting-period clauses, IRDAI standard definitions).

Each allowlisted hit is still counted and written to the dataset-mode report (`allowlisted_hits`), so an allowlist that grows to hide real leaks would show up.

**Planted cases:**
- A 20-token findings span copied into `insurer_position` without quotes → fails.
- The same span inside quotation marks in both sections, and on the allowlist → passes.
- A 12-token shared span → passes (below n); proves the threshold is applied as configured.

**On failure:** if the shared text is genuine policy wording, add it to the allowlist **in its own commit** with the source clause named; otherwise treat as §4.1.

### 4.3 `test_marker_probe.py` — L1

**Asserts:** no findings or award marker from `config.yaml` `segment.markers.<rule>` appears anywhere in `facts_text`, matched case-insensitively as a phrase (not only as a heading line).

**Why:** the segmenter already drops documents with `marker_in_facts` (`segmentation-rules.md` §5), but only for heading-like lines. A marker phrase mid-paragraph ("…as set out in my final decision below…") signals that reasoning has crept in. This probe also catches a regression where someone disables the segmenter's validation step.

**Planted cases:** "My final decision" mid-sentence in a FOS complaint; "AWARD" as a heading inside CIOINS `insurer_position`; Hindi heading `निर्णय` inside facts.

**Known false-positive and its rule:** the word "Decision" is an FSPO award marker and also common English ("the insurer's decision to decline"). For FSPO, the marker probe matches only `Decision` as a **heading line** or the full phrases in the marker list; this exception is in `config.yaml`, not in test code.

### 4.4 `test_lexicon_rate.py` — L2

**Asserts (hard):**
- `lexicon_hits` in the processed record equals a fresh count of lexicon terms in `facts_text`.
- The rate table has one row per source × label and no missing combination.

**Computes and logs (not a failure):** share of `facts_text` with ≥ 1 lexicon term, per source × label, written to `reports/leak/lexicon_rate.csv` in dataset mode. The PR 14 report uses this table and runs the masked vs unmasked ablation (`leakage-contract.md` §4 L2).

**Why not a hard fail:** complainants legitimately call a rejection unfair, so a non-zero rate is expected. What matters is a **large difference between labels**, which is a modelling signal, not a code bug.

**Warning threshold:** if the rate for `upheld` and `rejected` differs by more than 15 percentage points within one source, the test emits a `pytest` warning and the dataset-mode summary marks it `CHECK`. The PR 7 description must comment on any `CHECK`.

### 4.5 `test_input_columns.py` — L1 (code path)

**Asserts:**
- `claimsense.features.build_inputs(df)` (used by every baseline, the fine-tune data loader and `predict()`) returns features derived only from `facts_text`.
- Passing a dataframe whose `findings_text` and `label` columns are replaced with random strings produces **identical** model inputs (byte-equal token IDs / feature matrix).
- Passing a dataframe **without** `findings_text` and `label` works (the builder does not even read them).

**Why:** the data probes prove the column `facts_text` is clean, but nothing stops a training script from concatenating `findings_text` "for context". That would silently turn the classifier into a reader. This test makes the only sanctioned input path provably blind to the answer columns.

**Planted case:** a test-only builder variant that appends `findings_text` → the identity assertion fails.

### 4.6 `test_temporal_split.py` — L3

**Asserts:**
- train: every `decision_date` ≤ `split.train_end`; val: `train_end` < date ≤ `val_end`; test: date > `val_end`.
- The `split` column stored in the parquet equals the split recomputed from the date (the split is fixed at build time and never recomputed differently later).
- No `doc_id` appears in more than one split file.
- *(from PR 12)* The calibrator fitting function, called through a spy, receives only indices that belong to val; `models/thresholds.json` records `fit_split: "val"`. Training and tuning entry points raise if given a path to `test.parquet` without the `--report` flag.

**Why:** a random split lets a 2025 decision teach the model about the very trends it is later tested on. The val-only rule stops the calibrator from quietly fitting to test, which would make test ECE look better than it is.

**Planted cases:** a 2025 record labelled `train`; a calibrator fit call that includes one test index.

### 4.7 `test_cross_split_dedup.py` — L4

**Asserts:**
- For every pair of records in different splits, MinHash-estimated Jaccard over shingled `facts_text` is below `dedup.jaccard_threshold`. Candidate pairs come from LSH, and each candidate is re-checked with exact Jaccard before reporting.
- In each near-duplicate cluster recorded in `dedup_log.csv`, the kept record has the earliest `decision_date` (ties → lowest `doc_id`).
- Dedup ran **before** the split: the build log shows `dedup` finishing before `split` (`dataset-versioning.md` §6).

**Why:** a re-issued award, a provisional plus final decision, or an office re-upload is the same dispute twice. If the copies land in train and test, the model is graded on a case it has already seen.

**Planted cases:** an exact copy across train and test; a near copy (one paragraph reworded, anonymiser indices shuffled) across val and test; a cluster where a later copy was kept.

**Performance:** LSH keeps this under 30 s on fixtures and a few minutes on the full dataset; the exact re-check removes LSH false positives.

### 4.8 `test_retrieval_dates.py` — L5

**Asserts:**
- `search()` has no default for `before` and raises `TypeError` when it is missing.
- **Property test (Hypothesis):** for random `before` dates across the index's date range and random fixture queries, every returned precedent has `decision_date < before` (strictly).
- With `exclude_doc_id` set, the query document is never returned, even when it is the nearest neighbour.
- When fewer than `k` decisions exist before the date, fewer are returned; the filter is never relaxed to fill the list.
- `predict()` with `query_date=None` passes today's date to `search()`.

**Why:** a precedent from after the query date reveals how such cases are decided *now*, which is information the user's case could not have had. The filter has to hold for every call, so a single example is not enough; the property test covers edge dates (exactly equal, first and last day of the index).

**Planted case:** a search implementation that uses `<=` instead of `<` → fails on the equal-date edge.

---

## 5. When a probe fails

| Situation | Action | Never |
|---|---|---|
| L1 hit on fixtures (CI) | The code change broke segmentation or normalisation; fix before merge | Skip, `xfail`, or loosen config in the same PR |
| L1 hit on real data | Tighten the marker rule (new rule version) or drop the document; re-run segmentation for that source/office; redo the hand check for that rule | Hand-edit the text |
| L2 `CHECK` | Comment in the PR; PR 14 ablation decides masking | Treat as a hard block |
| L3/L4 hit | Rebuild the dataset; it gets a new hash (`dataset-versioning.md` §4) | Patch the parquet |
| L5 hit | Fix `search()`; re-run any evaluation that used retrieval | Filter results after retrieval as a workaround |
| Planted case no longer caught | The probe was weakened; revert the change | Delete the planted case |

Changing any value under `leak:` or `dedup:` in `config.yaml` needs its own commit with the reason, and the PR description must show the planted cases still fail.

---

## 6. Evidence recorded per PR

| PR | Paste into description |
|---|---|
| 6 | CI `leak` job link; dataset-mode summary for L1 + L2 over all labelled documents; count of allowlisted n-gram hits |
| 7 | Dataset-mode summary for all probes on dataset v1; `lexicon_rate.csv` with any `CHECK` explained; dedup cluster count |
| 12 | Val-only assertion output |
| 13 | Property-test example count and seed profile |
| 14 | Facts-only vs findings-included gap and lexicon masking ablation (reported, not tested here) |
| Every later PR | CI `leak` job green |

Example dataset-mode summary line:

```text
leak v1a3f9c2: docs 2,184 · L1 sentence 0 · L1 ngram 0 (allowlisted 37) · L1 marker 0 · L2 CHECK 0 · L3 0 · L4 0 (clusters 41) · L5 n/a
```
