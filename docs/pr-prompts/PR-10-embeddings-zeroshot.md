# PR 10 · Embedding classifier + zero-shot LLM

| | |
|---|---|
| **Branch** | `feat/embeddings-zeroshot` |
| **Depends on** | PR 9 |
| **Covers** | FR-10 (rest) · **Risks** R11 |
| **Read first** | `docs/modelling/baselines.md` (B4, B5), `docs/modelling/prompt-spec.md` (all, esp. §1 versioning, §3 provider, §6 cache), `docs/operations/configuration.md` §3.5, §3.8, §5, `docs/responsible-ai/privacy-impact-assessment.md` (P-R7) |
| **Done when** | Both B4 and B5 beat TF-IDF on val, or the gap is explained in the PR description |

---

## 1. Goal

Two stronger baselines and two shared components used later: the **encoder wrapper** (reused by retrieval in PR 13) and the **LLM client** with versioned prompts (reused by the explainer in PR 13).

## 2. Files to add

| File | Contents |
|---|---|
| `src/claimsense/models/embed.py` | `Encoder` protocol (`encode(texts) -> np.ndarray`, `dim`, `name`, `revision`); `SentenceTransformerEncoder(name, revision)` (CPU) |
| `src/claimsense/llm/client.py` | `LLMClient` protocol; `GroqClient`, `GeminiClient` (provider from `llm.provider`, key from env, temperature 0, JSON mode, timeout, retries); disk cache under `paths.cache_dir` keyed by (provider, model, prompt_id, prompt hash, input hash) when `llm.cache` and not live; `ExplainerUnavailableError` with the env var name if the key is missing |
| `src/claimsense/prompts/P-ZS-v1.txt` | Zero-shot prompt per `prompt-spec.md` |
| `src/claimsense/prompts/registry.yaml` | `P-ZS-v1: sha256` |
| `src/claimsense/prompts/__init__.py` | `load_prompt(id)` verifies the hash against the registry |
| `tests/stubs/stub_llm.py` | Canned JSON by input hash; can simulate malformed JSON, timeout |
| `tests/stubs/hashing_embedder.py` | Deterministic hashing encoder (fixed dim), implements `Encoder` |
| `tests/unit/test_zero_shot_parse.py`, `tests/unit/test_llm_client.py`, `tests/unit/test_prompts.py`, `tests/slow/test_embed_real_model.py` | See §4 |

## 3. Files to modify

| File | Change |
|---|---|
| `src/claimsense/models/baselines.py` | `EmbedLogReg(encoder)` (B4) and `ZeroShotLLM(client)` (B5: invalid/unparseable answers counted, mapped to a uniform distribution, rate logged) |
| `src/claimsense/models/__main__.py` | `--only B4,B5`; B5 runs on **val only** |
| `tests/unit/test_baselines_smoke.py` | B4 with `hashing_embedder`, B5 with `stub_llm` |
| `config.yaml` | `baselines.embed_encoder`, `llm` block (pin `model` and `model_checked_on`) |
| `scripts/ci_guard.sh` | Rule `prompts-hashed`: every file in `src/claimsense/prompts/*.txt` has a matching hash in `registry.yaml` |
| `pyproject.toml` | `sentence-transformers`, `torch` (CPU via uv index), `groq` and/or `google-genai`, `python-dotenv` |
| `reports/baseline-results.md` | B4, B5 rows via `export_table` |
| `CHANGELOG.md` | One line |

## 4. Tests to write

- **`test_prompts.py`**: editing a prompt without updating the registry → `load_prompt` raises; guard rule fails in a temp repo.
- **`test_llm_client.py`**: missing key → `ExplainerUnavailableError` naming the variable; cache hit avoids a second call (stub transport); temperature/seed sent; no call made when `CLAIMSENSE_ENV=ci` without a stub (raises).
- **`test_zero_shot_parse.py`**: valid JSON → label; malformed → counted invalid; label outside enum → invalid.
- **`tests/slow/test_embed_real_model.py`** (`slow`): real `bge-small` encodes 2 texts, dim matches config.

## 5. E2E tests

**`tests/e2e/test_e2e_10_embeddings_zeroshot.py`**:
- B4 (hashing embedder) and B5 (stub LLM answering from the corpus keyword signal) run on the world; MLflow has 5 baseline runs total.
- The stub LLM receives **only** `facts_text` strings (assert every prompt sent contains no ground-truth findings/award sentence) — the leakage contract holds for API calls too.
- No socket opened during the whole e2e session (pytest-socket).
- Contracts file extended for B4/B5 meta.

## 6. Definition of done

`make pr-check` → ALL CHECKS PASSED with **no API keys set**; raise the floor.

## 7. Manual checks (Diya)

- [ ] Put `GROQ_API_KEY` (or `GEMINI_API_KEY`) in `.env`. Run `uv run python -m claimsense.models baselines --only B4,B5`.
- [ ] Paste macro-F1 B1–B5. If B4/B5 don't beat B3, write why.
- [ ] In the PR: provider free-tier limits, data-retention setting chosen (P-R7), and confirmation only anonymised `facts_text` was sent.
- [ ] Optional: run `slow.yml` is added in PR 13; for now `make test-slow` locally.
