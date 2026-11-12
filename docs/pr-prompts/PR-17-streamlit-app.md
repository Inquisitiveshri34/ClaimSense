# PR 17 · Streamlit app

| | |
|---|---|
| **Branch** | `feat/app` |
| **Depends on** | PR 16 |
| **Covers** | FR-18, FR-19, NFR-11(b), NFR-12 · **Risks** R12, R13 |
| **Read first** | `docs/operations/user-guide.md`, `docs/responsible-ai/responsible-use.md`, `docs/architecture/pipeline-interface.md` §2 ("What the app shows"), §3 messages, `docs/requirements/user-stories.md`, `docs/operations/configuration.md` §3.9 (`app`), §6 |
| **Done when** | The app runs locally from one command (`make app`) |

---

## 1. Goal

A local app a non-technical person can use, with four pages and the disclaimer on every page. The app is a **thin shell over `predict()` and the report data** — no model logic lives in `app/`.

## 2. Files to add

| File | Contents |
|---|---|
| `app/Home.py` | What ClaimSense does and does not do; disclaimer |
| `app/pages/1_Predict.py` | Facts text area (with the guidance from `user-guide.md`), country select (default `app.default_country`), Predict button → `predict()`. Shows per interface §2 table: outcome + probability in words ("about 7 in 10 similar cases", rounding `app.probability_rounding`, exact on hover), precedents with country/year/label/excerpt, cited explanation with citation chips, per-code abstain messages from interface §3; catches `ExplainerUnavailableError` → shows prediction + "explanation unavailable" |
| `app/pages/2_Precedent_Explorer.py` | Filter by rejection reason, insurer type, year, source; table of anonymised precedents (from the index sidecar) |
| `app/pages/3_Model_Card.py` | Metrics table, reliability plot, abstain rates, known failure modes — read from generated report data (`reports/*.json` or `MODEL_CARD.md` sections), not recomputed |
| `app/pages/4_Data_Explorer.py` | Dataset size, class balance, sources, data card — from `build_meta.json` / `DATA_CARD.md` |
| `app/components/disclaimer.py` | `render_disclaimer()`; the one text from `responsible-use.md` |
| `app/components/format.py` | `probability_in_words(p)`, abstain message lookup — pure functions, unit tested |
| `app/state.py` | `@st.cache_resource` wrapper around `pipeline.load()`; artefact dir from `CLAIMSENSE_OUT_DIR` |
| `.streamlit/config.toml` | As `configuration.md` §6 |
| `tests/app/test_pages.py`, `tests/unit/test_app_format.py` | See §4 |

## 3. Files to modify

`src/claimsense/evaluate/report.py` (also write `reports_dir()/report_data.json` consumed by the Model Card page), `config.yaml` (`app`), `pyproject.toml` (`streamlit`), `Makefile` (`app`: `uv run streamlit run app/Home.py`), `scripts/ci_guard.sh` (rule: every file in `app/pages/` calls `render_disclaimer`), `CHANGELOG.md`.

## 4. Tests to write

- **`test_app_format.py`**: 0.68 → "about 7 in 10"; 0.05 / 0.95 edge wording; every abstain code has a message identical to interface §3.
- **`test_pages.py`** (Streamlit `AppTest`, pipeline injected with stubs via `app/state.py` override): all 4 pages + Home render without exceptions; disclaimer text present on each; Predict with a confident query shows outcome, precedents and explanation; `LOW_CONFIDENCE` query hides outcome and shows "Similar past cases"; `OFF_TOPIC` shows its message and no precedents; explainer raising → prediction still shown with warning; explorer filter reduces rows.

## 5. E2E tests

**`tests/e2e/test_e2e_17_app.py`**:
- `AppTest` with `CLAIMSENSE_OUT_DIR`/`CLAIMSENSE_DATA_DIR` pointing at the world and **no injection**: the app loads the real world artefacts through `pipeline.load()` (stub LLM/NLI/encoder only).
- Submit a world test record's facts on Predict → precedents displayed match `predict()` called directly with the same input (app adds nothing and drops nothing).
- Model Card page numbers equal the world report's `report_data.json`; Data Explorer counts equal the world `build_meta.json`.
- Earlier e2e files pass unchanged.

## 6. Definition of done

`make pr-check` → ALL CHECKS PASSED; raise the floor.

## 7. Manual checks (Diya)

- [ ] `make app` → walk through all pages with: one confident case, one borderline, one motor claim, one Hindi sentence, one 20-character input.
- [ ] Remove the API key from `.env` and restart → Predict still works without an explanation.
- [ ] Plain-language check (NFR-12): ask one non-technical person to read the Predict page; note anything confusing in the PR.
