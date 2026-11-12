# How to use these PR prompts (for Diya)

This folder has one prompt file per PR (`PR-01` … `PR-18`) plus one shared rules file (`00-CONVENTIONS.md`). Each PR file is written for **Claude Code**: it tells Claude Code what to build, which spec docs to read, which files to add or change, which tests to write, and how to prove the PR works before you merge it.

---

## 1. One-time setup

1. Copy this folder into the repo as `docs/pr-prompts/`.
2. Commit it straight to `main` **before PR 1**, because PR 1 turns on branch protection:
   ```bash
   cd ~/Desktop/ClaimSense
   mkdir -p docs/pr-prompts && cp ~/Downloads/pr-prompts/*.md docs/pr-prompts/
   git add docs/pr-prompts && git commit -m "docs: add per-PR build prompts" && git push
   ```
3. Install the GitHub CLI if you don't have it (`brew install gh`, then `gh auth login`). Claude Code uses it to open each PR for you.
4. Install the tools listed in `docs/operations/setup.md` §2 (Python 3.11, uv, make, Tesseract).

---

## 2. Running one PR

Start Claude Code in the repo folder, on an up-to-date `main`, and paste:

```text
Read docs/pr-prompts/00-CONVENTIONS.md, then docs/pr-prompts/PR-03-india-collector.md.
Implement PR 3 exactly as described. Create the branch, write the code and all tests,
run `make pr-check` until it passes, commit, push, and open the PR with gh.
Do not merge. Stop and tell me if anything in the spec docs contradicts the prompt.
```

Change the file name for each PR. Do **one PR per Claude Code session**, so each session starts clean.

---

## 3. Your pre-merge checklist (every PR)

Run these yourself on the PR branch before you click **Merge**:

```bash
git fetch && git checkout <branch> && git pull
uv sync --frozen --all-extras
make pr-check          # lint, unit, leak, e2e, guard, fixture manifest, test-count floor
```

Then:

- [ ] `make pr-check` prints **ALL CHECKS PASSED**.
- [ ] GitHub shows all required checks green on the latest commit.
- [ ] The PR's own **Manual checks** section (at the bottom of each PR file) is done and its results are pasted into the PR description.
- [ ] If the PR claims a data gate and you have real data: `make test-data` passes. A *skip* counts as a fail.
- [ ] The PR description lists FR/NFR IDs and risk IDs.
- [ ] Merge with **Squash and merge**. Then `git checkout main && git pull`.

---

## 4. Why the end-to-end tests matter

From PR 1 onward there is a folder `tests/e2e/`. It builds a small **synthetic** world (fake ombudsman sites serving about 90 made-up decisions) and runs the *real* code through every stage built so far:

```text
PR 3–4   collect  →  PR 5 parse/segment  →  PR 6 label/anonymise/leak  →  PR 7 dataset
→  PR 9–10 baselines  →  PR 11 tiny fine-tune  →  PR 12 calibrate  →  PR 13 index + explain
→  PR 14–15 report  →  PR 16 predict()  →  PR 17 app  →  PR 18 reproduce
```

Each PR adds its stage **on top of the previous stages' real outputs**, not on hand-made fixtures. So if PR 12 changes something that breaks what PR 7 produced, the e2e suite fails before you merge. A test-count floor (`tests/.test_count_floor`) also stops any PR from quietly deleting earlier tests.

---

## 5. If something goes wrong

| Situation | What to do |
|---|---|
| Claude Code says the spec and the prompt disagree | The spec doc in `docs/` wins for behaviour; the prompt wins for scope. Decide, note it in the PR description |
| A test needs real data you don't have yet | It must be marked `local_data` and skip in CI. It must never be deleted to make CI pass |
| `make pr-check` fails on a test from an earlier PR | That is a regression. Fix the new code, not the old test |
| You want to add something not in the PR file | Put it in `docs/planning/backlog-v2.md` instead (risk R15) |
