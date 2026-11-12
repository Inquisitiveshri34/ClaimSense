#!/usr/bin/env bash
# Repository guard (docs/operations/ci-cd.md §3.4). Run by the CI `guard` job,
# by `make pr-check` and by tests/unit/test_guard.py.
#
# Each rule looks only at files tracked by git in the repository that contains
# the current directory, prints its name with PASS or FAIL, and lists what it
# found. The script exits non-zero if any rule fails.
#
# Rules (later PRs add more):
#   no-data-tracked       nothing under data/ except data/.gitkeep, data/README.md
#   no-pdfs               no *.pdf outside tests/fixtures/
#   no-secrets-files      no .env, kaggle.json or *.pem
#   no-network-in-tests   no http:// or https:// in tests/ outside
#                         tests/fixtures/**/urlmap*.yaml and tests/e2e/corpus.py

set -u

cd "$(git rev-parse --show-toplevel)" || exit 2

failed=0

report() {
  # report <rule name> <offending lines, empty when the rule passes>
  if [ -z "$2" ]; then
    echo "PASS  $1"
  else
    echo "FAIL  $1"
    printf '%s\n' "$2" | sed 's/^/        /'
    failed=1
  fi
}

report "no-data-tracked" \
  "$(git ls-files -- data | grep -v -x -e 'data/.gitkeep' -e 'data/README.md')"

report "no-pdfs" \
  "$(git ls-files | grep -i '\.pdf$' | grep -v '^tests/fixtures/')"

report "no-secrets-files" \
  "$(git ls-files | grep -E '(^|/)(\.env|kaggle\.json)$|\.pem$')"

report "no-network-in-tests" \
  "$(git grep -nIE 'https?://' -- tests \
       ':(exclude,glob)tests/fixtures/**/urlmap*.yaml' \
       ':(exclude)tests/e2e/corpus.py')"

if [ "$failed" -ne 0 ]; then
  echo "GUARD FAILED"
  exit 1
fi
echo "GUARD PASSED"
