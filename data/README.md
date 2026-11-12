# `data/`: local only, never committed

Everything in this folder except this file and `.gitkeep` is git-ignored. The
pre-commit hook `block-data-paths` and the CI `guard` job both reject any other
path under `data/`. Raw and interim data never leave the laptop
(`docs/responsible-ai/privacy-impact-assessment.md`, P-R5).

| Folder | Holds | Written by |
|---|---|---|
| `raw/<source>/` | Downloaded decision PDFs and pages, exactly as published | The collectors (PRs 3–4) |
| `interim/` | Extracted and segmented text, before anonymisation | Parse and segment (PR 5) |
| `processed/v<hash>/` | The anonymised, labelled dataset version; `processed/LATEST` names the current one | `make build` (PR 7) |
| `manifests/` | Per-source download manifests (URL, date, file hash) | The collectors (PRs 3–4) |
| `cache/` | LLM response cache for offline runs | Zero-shot baseline and explainer (PRs 10, 13) |

The folders are created by the code that first writes to them. To keep the data
somewhere else, set `CLAIMSENSE_DATA_DIR` (`docs/operations/configuration.md` §5.2).
