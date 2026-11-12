# ClaimSense — Test Strategy

> How ClaimSense is tested: the test layers, where each runs, what CI blocks on, how tests run with no real data and no network, and which tests each PR adds. The data is git-ignored and two of three sources may never be collected live, so the suite is built to prove the code is correct on fixtures in CI, and to prove the *data* is correct on the real dataset locally, with both results recorded on the PR.

**Author:** Diya Shrivastava · **Owning PR:** 1 (scaffold, CI, conventions); every later PR adds its own tests · **Status:** Planned

**Related:** `acceptance-criteria.md` (every check this suite implements), `non-functional-requirements.md` §4 (quality gates), `leakage-contract.md` §6, `testing/leak-probe-tests.md`, `testing/test-fixtures.md`, `data/collection-runbook.md` §1, `pipeline-interface.md` §8, NFR-01, NFR-05, NFR-08, NFR-10, risks R3, R14.

---

## 1. Principles

1. **CI never touches the network or real data.** Collectors read saved pages, the explainer is a stub, and no file under `data/` exists in CI. A test that needs the internet is a bug (risk R14, NFR-08).
2. **Two modes for data checks.** Every data-quality test (leak probes, PII scan, schema, split, dedup) runs on **fixtures in CI** and on the **real processed dataset locally**. The fixture run proves the check works; the local run proves the data passes. Both results go in the PR description.
3. **A guard is only trusted after it has been seen to fail.** Each leak probe and PII check has a planted-violation fixture that must make it fail (`testing/leak-probe-tests.md` §3).
4. **Tests read `config.yaml`.** Thresholds (n-gram size, MinHash threshold, `abstain.threshold`, `min_entailment`, `input.min_chars`) are never copied into test files, so tests and pipeline cannot drift apart.
5. **Deterministic by default.** Seeds come from `config.yaml`; the only tolerated non-determinism is GPU training, which is not run in CI.
6. **Leakage failures block.** A red leak probe is never skipped, marked `xfail`, or merged around. Suspiciously good metrics are treated as a leakage bug until proven otherwise (R3).

---

## 2. Test layers

| Layer | What it proves | Inputs | Runs in | Speed budget | Example |
|---|---|---|---|---|---|
| **Unit** | One function behaves on fixtures | Small strings, tiny dataframes | CI, every PR | < 1 s each | Label mapping, one anonymiser entity, abstain-code precedence |
| **Collector** | Scrapers parse saved pages, resume, and stay polite | Saved HTML/PDF + fake HTTP transport + mocked clock | CI, every PR | < 5 s each | Listing parser, `verify`, ≥ 2 s interval |
| **Leak-probe** | No answer text reaches model input; no future data or duplicate cases cross splits | Fixture records (CI); full processed dataset (local) | CI every PR from PR 6; local before PR 7 freeze and on every dataset version | < 30 s on fixtures | Sentence probe, retrieval date property test |
| **Integration** | Several stages chain correctly on saved sample data | Fixture PDFs → segments → labelled → processed mini-dataset | CI, every PR | < 60 s total | Parse → segment → label → anonymise on 12 PDFs |
| **Pipeline** | `predict()` honours its contract | Fixture queries + tiny artefacts (stub classifier, toy index, stub explainer, stub NLI) | CI from PR 16 (retrieval parts from PR 13) | < 20 s total | Schema, abstain codes, no future precedents, CPU-only |
| **Slow** | Real heavy models behave | Real NLI cross-encoder, real embedding model | Local / manual workflow, not on every PR | minutes | NLI drops an injected unsupported sentence |
| **Metric** | A logged number meets its threshold | Real dataset + trained models | Experiment tracker + `make report` | — | Test ECE ≤ 0.05, beats every baseline |
| **Manual** | Human judgement on a fixed sample | Audit samples per `data/manual-audit-protocol.md` | Recorded in PR description | — | 50-doc segmentation, 100-doc PII, 40-case faithfulness |

**Not tested automatically (by design):** live site behaviour (checked by the runbook's `verify` and `report` after a real run), GPU training (checked by the PR 11 notebook), plain-language quality (NFR-12 manual review), and laptop latency (NFR-06 benchmark run locally, numbers pasted into the PR).

---

## 3. Repository layout

```text
tests/
├── conftest.py              # shared fixtures, config loader, network block, seed setup
├── unit/
│   ├── test_schema_enums.py
│   ├── test_config.py
│   ├── test_label_mapping.py
│   ├── test_anonymise_entities.py
│   ├── test_anonymise_kept.py
│   ├── test_anonymise_consistency.py
│   ├── test_anonymise_allowlist.py
│   ├── test_segment_rules.py
│   ├── test_citation_structural.py
│   ├── test_calibration_math.py
│   └── test_abstain_codes.py
├── collect/
│   ├── test_cioins_listing.py
│   ├── test_fos_listing.py
│   ├── test_fspo_listing.py
│   ├── test_manifest_schema.py
│   ├── test_resume.py
│   ├── test_verify.py
│   └── test_politeness.py   # NFR-08: interval, one worker, User-Agent, Retry-After
├── leak/                    # see testing/leak-probe-tests.md
│   ├── test_sentence_probe.py
│   ├── test_ngram_probe.py
│   ├── test_marker_probe.py
│   ├── test_lexicon_rate.py
│   ├── test_input_columns.py
│   ├── test_temporal_split.py
│   ├── test_cross_split_dedup.py
│   └── test_retrieval_dates.py
├── integration/
│   ├── test_parse_text_and_ocr.py
│   ├── test_parse_to_labelled.py
│   ├── test_pipeline_order.py
│   ├── test_pii_scan.py
│   ├── test_dataset_build.py
│   ├── test_index_build.py
│   └── test_report_command.py
├── pipeline/
│   ├── test_predict_schema.py
│   ├── test_off_topic.py
│   ├── test_no_future_precedents.py
│   ├── test_citation_filter.py
│   ├── test_errors.py
│   └── test_cpu_only.py
├── app/
│   └── test_pages.py        # Streamlit AppTest: 4 pages render, disclaimer on each
├── slow/
│   └── test_nli_real_model.py
├── bench/
│   └── bench_latency.py     # not collected by pytest; run with `make bench`
└── fixtures/                # see testing/test-fixtures.md
```

Test files are added by the PR that owns the behaviour (§7). A directory may exist before its tests do.

---

## 4. Markers and how to run

Markers are registered in `pyproject.toml` with `--strict-markers`, so a typo fails the run.

| Marker | Meaning | Default run? |
|---|---|---|
| *(none)* | Unit, collector, integration, pipeline, app | ✅ |
| `leak` | Leak-probe tests (fixture mode) | ✅ |
| `local_data` | Needs `data/processed/` or real artefacts under `models/`/`index/`; auto-skipped with a reason if absent | ❌ in CI, ✅ locally via `make test-data` |
| `slow` | Loads a real heavy model | ❌ |

| Command | Runs | When |
|---|---|---|
| `make lint` | `ruff check .` and `black --check .` | Before every push; CI |
| `make test` | `pytest -m "not slow and not local_data"` | Before every push; CI |
| `make test-leak` | `pytest tests/leak -m leak` | After any change to parse, segment, label, anonymise, dataset or retrieve |
| `make test-data` | `pytest -m local_data` — leak probes, PII scan, schema, split and dedup over the real processed dataset | Before PR 6 and PR 7 merge; every new dataset version; before PR 18 |
| `make test-slow` | `pytest -m slow` | PR 13, PR 16, PR 18, and after changing `cite_check.model` |
| `make bench` | `python tests/bench/bench_latency.py` | PR 16 and PR 18 (NFR-06) |
| `make verify-data` | `python -m claimsense.collect verify` | After every real collection run |

`local_data` tests never fail because data is missing; they skip with `"data/processed/ not present — run make build first"`. A skip in a PR that claims a data gate is treated as **not passed**.

---

## 5. CI (GitHub Actions)

Workflow `.github/workflows/ci.yml`, triggered on every push and pull request.

| Job | Steps | Blocks merge |
|---|---|---|
| `lint` | Install from lock file → `ruff check` → `black --check` | ✅ |
| `test` | Install from lock file (CPU-only torch) → `pytest -m "not slow and not local_data"` with `--disable-socket` (pytest-socket), `CUDA_VISIBLE_DEVICES=""`, `CLAIMSENSE_ENV=ci` | ✅ |
| `leak` | `pytest tests/leak -m leak` as its own job, so a leakage failure is visible by name in the PR checks | ✅ from PR 6 |
| `guard` | Fails if any file under `data/`, `models/*.safetensors` or a `.env` is tracked; fails if a test file contains `http://` or `https://` outside `tests/fixtures/` URL maps | ✅ |

Workflow `.github/workflows/slow.yml` runs `make test-slow` on manual dispatch only; it caches the NLI model and does not block merges.

**Environment:** Python 3.11, Ubuntu, pinned lock file (NFR-05). Hugging Face downloads are disabled in the default job (`HF_HUB_OFFLINE=1`), which is what forces every model in non-slow tests to be a stub or tiny fixture.

**Branch protection on `main`:** `lint`, `test`, `leak` and `guard` required; linear history; no direct pushes.

---

## 6. Gates and how evidence is recorded

| Gate | Check | Mode | Evidence in PR description |
|---|---|---|---|
| CI | `lint`, `test`, `leak`, `guard` green | CI | Link to the run |
| Leak probes on data | 0 failures across the processed dataset | Local, `make test-data` | Pasted summary line from `reports/leak/leak_probe_summary.txt` |
| PII scan on data | 0 regex hits on the full processed set + 0 hits on 100-doc manual sample | Local + manual | Scan summary + audit ID |
| Segmentation | ≥ 95% on 50 hand-checked docs | Manual | Audit ID A1 + score |
| Dataset freeze | Rebuild gives the same `dataset_version` hash | Local | Both hashes |
| Model | Beats every baseline on val; test ECE ≤ 0.05 | Metric | Run IDs + numbers |
| Release | Fresh clone reproduces test metrics | Manual, clean environment | Command log + metric table |

The PR template (`.github/pull_request_template.md`) has one checkbox per row of `acceptance-criteria.md` §4 for that PR, plus fields for these pasted results.

---

## 7. Tests added per PR

| PR | Tests added | Layer | Covers |
|---|---|---|---|
| 1 | `test_config.py`, placeholder test, `conftest.py` (network block, seeds, config loader) | Unit | NFR-05(a), NFR-10 |
| 2 | `guard` job: `data/raw/` ignored | CI | NFR-09(c) |
| 3 | `test_cioins_listing.py`, `test_manifest_schema.py`, `test_resume.py`, `test_verify.py`, `test_politeness.py` | Collector | FR-01–03, NFR-08 |
| 4 | `test_fos_listing.py`, `test_fspo_listing.py`; shared-schema case in `test_manifest_schema.py` | Collector | FR-01–03, FR-02(c), NFR-08 |
| 5 | `test_parse_text_and_ocr.py`, `test_segment_rules.py` (incl. marker-in-facts drop) | Unit + Integration | FR-04, FR-05 |
| 6 | `test_label_mapping.py`, all `test_anonymise_*.py`, `test_pipeline_order.py`, `test_pii_scan.py`, `test_parse_to_labelled.py`; leak probes `test_sentence_probe.py`, `test_ngram_probe.py`, `test_marker_probe.py`, `test_lexicon_rate.py`, `test_input_columns.py` | Unit + Integration + Leak | FR-06, FR-07, NFR-01, NFR-02 |
| 7 | `test_dataset_build.py`, `test_temporal_split.py`, `test_cross_split_dedup.py` | Integration + Leak | FR-08, FR-09, NFR-05 |
| 8 | Notebook executes end to end (`nbclient`, `local_data`) | Local | — |
| 9–10 | Baseline smoke tests on the mini-dataset (fit, predict, metrics keys present) | Unit | FR-10 |
| 11 | Adapter `meta.json` schema; no base weights tracked (`guard`) | Unit | FR-11(a, b) |
| 12 | `test_calibration_math.py` (ECE/Brier on known inputs); val-only case in `test_temporal_split.py` | Unit + Leak | FR-12, NFR-03 |
| 13 | `test_index_build.py`, `test_retrieval_dates.py`, `test_citation_structural.py`, `test_citation_filter.py`, `test_nli_real_model.py` (slow) | Integration + Leak + Slow | FR-13, FR-15, FR-16, NFR-04(a) |
| 14 | `test_report_command.py` (report builds from mini-dataset; required sections present) | Integration | FR-20, NFR-01(c) |
| 15 | Faithfulness audit loader: A6 file schema and agreement computation | Unit | NFR-04(b) |
| 16 | `test_predict_schema.py`, `test_abstain_codes.py`, `test_off_topic.py`, `test_no_future_precedents.py`, `test_errors.py`, `test_cpu_only.py`, `bench_latency.py` | Pipeline | FR-14, FR-17, NFR-06, NFR-07(b) |
| 17 | `app/test_pages.py` (four pages render; disclaimer on each; explorer filters) | App | FR-18, FR-19, NFR-11(b) |
| 18 | Fresh-clone reproduction script `scripts/reproduce.sh` (manual) | Manual | NFR-05(b) |

---

## 8. Stubs for external and heavy dependencies

| Dependency | In CI | Real version tested |
|---|---|---|
| Ombudsman websites | Fake HTTP transport serving saved pages from a URL map | Never in tests; runbook `verify` after real runs |
| Explainer LLM (Groq/Gemini) | `StubExplainer` returning canned JSON from `tests/fixtures/pipeline/explainer/` | Never in tests (paid/rate-limited); PR 13 dev-set run |
| NLI cross-encoder | `StubNLI` with scores keyed by (premise id, hypothesis) | `make test-slow` |
| Fine-tuned classifier | `StubClassifier` returning fixed logits per fixture query | Metric runs; PR 16 local integration with `local_data` |
| Embedding model | Tiny deterministic hashing embedder (fixed dimension) | `local_data` index test |
| Tesseract | Real binary installed in CI (`apt-get install tesseract-ocr`); one small scanned fixture | Same |
| Clock | Mocked monotonic clock in collector tests | — |

Stubs live in `tests/stubs/` and implement the same interfaces as the real classes, so swapping them is a constructor argument, not monkey-patching.

---

## 9. Coverage and quality

- **Coverage target:** ≥ 85% line coverage on `src/claimsense/{collect,parse,label,anonymise,dataset,retrieve,pipeline}`; reported in CI, not a hard gate. Training and notebook code are excluded.
- **Every bug gets a test.** A bug fix PR adds a failing fixture first; for leakage or PII bugs, that fixture becomes a planted-violation case.
- **Flaky tests** are fixed or deleted within the same PR; never retried automatically. Hypothesis property tests use a fixed `derandomize=True` profile in CI.
- **No sleeping.** Collector timing is tested with the mocked clock; no real `time.sleep` in tests.

---

## 10. Risks this strategy addresses

| Risk | How the suite responds |
|---|---|
| R3 Leakage | Leak probes in their own CI job + planted-violation self-tests + local full-dataset run + facts-vs-findings gap in the report |
| R5 PII exposure | Per-entity unit tests, full-dataset regex scan, manual 100-doc sample; committed fixtures are synthetic (`testing/test-fixtures.md` §2) |
| R14 Site changes | Collector tests on saved pages fail first; refresh procedure adds a new fixture alongside the old one |
| R10 Unfaithful explanations | Structural + stubbed NLI tests in CI; real NLI in slow suite; A6 audit |
| R15 Scope creep | Tests are added only by the PR that owns the behaviour (§7) |
