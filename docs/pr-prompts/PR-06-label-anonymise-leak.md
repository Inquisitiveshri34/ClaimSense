# PR 6 · Labels, anonymisation, leak probes

| | |
|---|---|
| **Branch** | `feat/label-anonymise` |
| **Depends on** | PR 5 |
| **Covers** | FR-06, FR-07, NFR-01, NFR-02 · **Risks** R3, R5, R6 |
| **Read first** | `docs/data/labelling-guide.md`, `docs/data/anonymisation-spec.md`, `docs/data/manual-audit-protocol.md` (A2), `docs/architecture/leakage-contract.md`, `docs/testing/leak-probe-tests.md` (all), `docs/testing/test-fixtures.md` §5–§6, `docs/operations/ci-cd.md` §3.4 |
| **Done when** | Leak tests pass (fixtures in CI, real data locally) and a PII scan of 100 sampled documents finds 0 hits |

---

## 1. Goal

Give every segmented document a 3-class label, remove personal data, and add the **leak probes** that prove no answer text reaches the model input. From this PR on, the `leak` CI job must collect tests and must pass.

## 2. Files to add

| File | Contents |
|---|---|
| `src/claimsense/label/outcomes.py` | `extract_label(award_text, source)` → `upheld` / `partially_upheld` / `rejected` / `"EXCLUDE"` (non-entertainable, withdrawn, settled) or raises `UnmappedOutcome`; FSPO/FOS prefer listing metadata when present; rules versioned |
| `src/claimsense/label/anonymise.py` | `Anonymiser` per spec: Presidio + custom recognisers (`in_phone`, `in_pin`, `in_aadhaar_like`, `in_pan_like`, `policy_number`, `claim_number`, UK postcode, honorific+name, Dr+name); same entity → same `[PERSON_n]` across all four sections of one doc; allowlist; longest-span wins, `[PERSON]` beats `[PROVIDER]` on ties; PIN only replaced near address cues; keeps insurer/TPA names, conditions, amounts, month-year dates, states |
| `src/claimsense/label/pii_scan.py` | `pii_scan(records) -> list[Hit]` regex post-check; hits quarantined to `data/_pii_quarantine/` and excluded |
| `src/claimsense/label/__main__.py` | `python -m claimsense.label run`: interim → labelled + anonymised records (`interim_dir()/labelled/*.jsonl`) with `facts_text = complaint + "\n\n" + insurer_position`; unmapped wordings logged to `reports/label/unmapped.csv` (wording only, anonymised); `audit-sample --n 100` for A2 |
| `src/claimsense/dataset/leak_probes.py` | Probes exactly per `leak-probe-tests.md`: sentence probe (normalised, anonymiser indices and amounts masked), n-gram probe (n from config, allowlisted policy quotes counted not failed), marker probe (per-source markers incl. Hindi; FSPO "the insurer's decision" allowed), outcome-word lexicon rate per label (`CHECK` if unbalanced), input-columns check (model input = only `facts_text`). `run_all(records) -> ProbeReport`; writes `reports/leak/leak_probe_summary.txt` |
| `tests/fixtures/label/wording.yaml` | Outcome sentences → expected label / `EXCLUDE` / unmapped |
| `tests/fixtures/anonymise/…` | All files listed in `test-fixtures.md` §5 |
| `tests/fixtures/leak/…` | `clean.jsonl`, `planted_sentence.jsonl`, `planted_ngram.jsonl`, `planted_marker.jsonl`, `policy_quote_allowed.jsonl`, `lexicon.jsonl` (each record has `synthetic: true`; planted records have `_planted`) |
| Unit tests | `tests/unit/test_label_mapping.py`, `test_anonymise_entities.py`, `test_anonymise_kept.py`, `test_anonymise_consistency.py`, `test_anonymise_allowlist.py` |
| Integration tests | `tests/integration/test_pipeline_order.py`, `test_pii_scan.py`, `test_parse_to_labelled.py` |
| Leak tests | `tests/leak/test_sentence_probe.py`, `test_ngram_probe.py`, `test_marker_probe.py`, `test_lexicon_rate.py`, `test_input_columns.py` |

## 3. Files to modify

`config.yaml` (`label`, `anonymise`; **V**), `config.py`, `pyproject.toml` (`presidio-analyzer`, `presidio-anonymizer`, pinned spaCy English model as a direct URL dependency or downloaded in setup — document which), `.github/workflows/ci.yml` (`leak` no longer tolerates "no tests collected"), `scripts/ci_guard.sh` (rules: the five probe files exist; every file under `tests/fixtures/leak` and `tests/fixtures/anonymise` has `synthetic: true` / is listed synthetic in FIXTURES.yaml; `_pii_quarantine/` never tracked), `scripts/block_data_paths.py` (`_pii_quarantine/`), `scripts/pr_check.sh` (leak step must collect ≥ 5 tests), `Makefile` (`label` target), `tests/fixtures/FIXTURES.yaml`, `CHANGELOG.md`.

## 4. Tests to write

- **Label**: every `wording.yaml` row maps as expected; unmapped wording raises and is logged; `EXCLUDE` rows never get a label.
- **Anonymise**: E01–E16 exact expected outputs; `kept.txt` unchanged spans survive; consistency across sections; allowlist; overlap tie-break; `pin_vs_amount`.
- **`test_pipeline_order.py`**: the label CLI never writes a record that has not passed through `Anonymiser` (spy) and `pii_scan`.
- **`test_pii_scan.py`**: 0 hits on `pii_scan_clean.jsonl`; every planted item in `pii_scan_planted.jsonl` found with correct type and location.
- **Leak probes — two modes each**: (a) fixture mode, marker `leak`: clean passes; **each planted file makes its probe fail and the report names the planted record and section**; `policy_quote_allowed` passes with the hit counted; FSPO allowed phrase does not trip; (b) `local_data` mode: same probes over `data/interim/labelled` or `data/processed/LATEST`.
- A **self-test**: if a probe function is replaced by `lambda *_: PASS`, the planted tests fail (prove the guard can fail).

## 5. E2E tests

`stages.py`: `run_label(world)` → `run_parse` then label CLI.

**`tests/e2e/test_e2e_06_label_anonymise.py`**:
- Every segmented doc gets the label in the corpus ground truth, or `EXCLUDE` where the corpus says so.
- **No fictional name, phone, PIN, postcode or policy number from the corpus ground truth appears anywhere** in the labelled output (search raw strings across all four sections) — the anonymiser works on generated documents it has never seen.
- `pii_scan` over all world records → 0 hits.
- `leak_probes.run_all` over the world records → all PASS; `facts_text` is exactly complaint + insurer_position.
- Inject one world record whose complaint contains its own award sentence → `run_all` FAILS (end-to-end proof the probe is live).
- Earlier e2e files pass unchanged.

## 6. Definition of done

`make pr-check` → ALL CHECKS PASSED (leak job collects ≥ 5 tests); raise the floor.

## 7. Manual checks (Diya)

- [ ] Real data: `make label` then `make test-data` → leak probes 0 failures, regex PII 0 hits. Paste the line from `reports/leak/leak_probe_summary.txt`.
- [ ] **Audit A2:** `python -m claimsense.label audit-sample --n 100`; read all 100 → 0 PII. Paste audit ID.
- [ ] Paste label distribution + unmapped wording count.
