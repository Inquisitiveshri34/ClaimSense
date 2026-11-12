# PR 5 · Parse and segment

| | |
|---|---|
| **Branch** | `feat/parse-segment` |
| **Depends on** | PR 4 |
| **Covers** | FR-04, FR-05 · **Risks** R1, R4 |
| **Read first** | `docs/data/segmentation-rules.md` (all), `docs/architecture/leakage-contract.md`, `docs/architecture/data-flow.md`, `docs/testing/test-fixtures.md` §5, `docs/data/manual-audit-protocol.md` (audit A1), `docs/operations/configuration.md` §3.3 |
| **Done when** | Segmenter ≥ 95% correct on 50 hand-checked documents (manual), and all automatic parse/segment tests + e2e pass |

---

## 1. Goal

Turn every stored document into text and split it into **complaint / insurer position / findings / award**. This is where the leakage contract starts: documents that cannot be segmented safely are **dropped with a reason**, never passed on.

## 2. Files to add

| File | Contents |
|---|---|
| `src/claimsense/parse/pdf_text.py` | `extract_text(path) -> ParsedDoc(text, pages, ocr_used, warnings)`: pdfplumber; if text < `parse.ocr_min_chars` → Tesseract at `ocr_dpi` with auto-rotation; two-column reading order (left before right); remove lines repeated on ≥ 50% of pages; unreadable → `ParseFailed(reason)` |
| `src/claimsense/parse/html_text.py` | FOS HTML → text preserving headings |
| `src/claimsense/parse/segment.py` | `segment(text, source, meta) -> Segments | Dropped`; per-source rule sets versioned by `segment.rules_version`; drop codes `order_violation`, `missing_findings`, `marker_in_facts`, `non_english` exactly as the spec |
| `src/claimsense/parse/__main__.py` | `python -m claimsense.parse run [--source X]`: for each `stored` manifest row → `interim_dir()/<source>/<doc_id>.json` (`doc_id`, `source`, `decision_date`, meta, four sections, `ocr_used`, `rules_version`) or a row in `interim_dir()/dropped.csv`; summary counts |
| `src/claimsense/parse/audit.py` | `sample_for_audit(n=50, seed)` stratified by source/office → writes `audits/A1-segmentation.csv` template (ids + boundaries only, **no text**) and `score_audit(path)` |
| `tests/fixtures/parse/*.pdf` | `text_layer`, `scanned`, `scanned_rotated`, `unreadable`, `two_column`, `header_footer_repeat` (built by `_build/make_pdfs.py`) |
| `tests/fixtures/segment/*.txt` + `expected/*.json` | The 14 files in `test-fixtures.md` §3 |
| `tests/integration/test_parse_text_and_ocr.py`, `tests/unit/test_segment_rules.py`, `tests/unit/test_parse_audit.py` | See §4 |

## 3. Files to modify

`config.yaml` (`parse`, `segment` per `configuration.md` §3.3; mark as **V**), `src/claimsense/config.py`, `.github/workflows/ci.yml` (`apt-get install -y tesseract-ocr tesseract-ocr-eng poppler-utils` in `test` and `e2e` jobs), `pyproject.toml` (`pdfplumber`, `pytesseract`, `pdf2image`, `langdetect` or equivalent), `Makefile` (`parse` target), `tests/e2e/corpus.py` (add 3 deliberately bad decisions per source: findings missing, award marker inside facts, non-English body; and make ~10% of CIOINS PDFs scanned images), `tests/fixtures/FIXTURES.yaml`, `CHANGELOG.md`.

## 4. Tests to write

- **`test_parse_text_and_ocr.py`**: `text_layer.pdf` → text, OCR not called (spy); `scanned.pdf`, `scanned_rotated.pdf` → OCR used, key phrase found; `unreadable.pdf` → `ParseFailed` with reason, counted; `two_column.pdf` → left-column sentence precedes right-column sentence; `header_footer_repeat.pdf` → repeated line removed.
- **`test_segment_rules.py`**: parametrised over every good fixture → section spans equal `expected/<name>.json`; each `bad_*` → `Dropped` with the right code; FSPO metadata page excluded from complaint; FOS quoted provisional finding inside complaint → `marker_in_facts` (or the spec's rule).
- **`test_parse_audit.py`**: sampler is deterministic for a seed, stratified, and the CSV it writes contains no section text.
- **`tests/leak/test_marker_probe.py` is NOT added yet** (PR 6), but add a unit test that no `Segments.complaint` or `.insurer_position` from the good fixtures contains any award marker from the per-source marker list.

## 5. E2E tests

`stages.py`: `run_parse(world)` → calls `run_collect`, then the parse CLI function.

**`tests/e2e/test_e2e_05_parse_segment.py`**:
- Every stored world document is either segmented or dropped; segmented + dropped == stored.
- The planted bad documents are dropped with the expected codes (match corpus ground truth); good documents are all segmented (≥ 95% — should be 100% on synthetic).
- For every segmented doc, `complaint` and `insurer_position` contain **no sentence** from that doc's ground-truth findings or award (first cross-stage leakage check).
- Scanned PDFs went through OCR and still segmented.
- Earlier e2e files pass unchanged.

## 6. Definition of done

`make pr-check` → ALL CHECKS PASSED; raise the floor; paste the e2e parse summary (parsed / OCR / dropped by code) in the PR.

## 7. Manual checks (Diya)

- [ ] With real data: `make parse` → paste summary.
- [ ] **Audit A1:** `uv run python -m claimsense.parse.audit sample --n 50`, check the 50 boundaries by hand in the CSV, `score` → ≥ 47/50. Paste audit ID + score.
