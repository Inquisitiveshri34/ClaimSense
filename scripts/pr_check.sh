#!/usr/bin/env bash
# Pre-merge gate (docs/pr-prompts/00-CONVENTIONS.md §9). Run with `make pr-check`.
#
# Runs every check in order, never stops at the first failure, then prints a
# PASS/FAIL table and a final `ALL CHECKS PASSED` or `CHECKS FAILED`.
#
#   1 lock        uv.lock valid and installed; requirements-lock.txt matches it
#   2 lint        make lint
#   3 test        make test, as CI runs it (no network, no GPU, no model hub)
#   4 leak        make test-leak
#   5 e2e         make test-e2e
#   6 guard       scripts/ci_guard.sh
#   7 test count  collected tests >= tests/.test_count_floor
#   8 data        make test-data, only when a processed dataset exists

set -u

cd "$(dirname "$0")/.." || exit 2

FLOOR_FILE="tests/.test_count_floor"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

names=()
results=()

record() {
  names+=("$1")
  results+=("$2")
}

run_step() {
  # run_step <name> <command...>: PASS if the command exits 0.
  local name="$1"
  shift
  echo
  echo "=== $name ==="
  if "$@"; then
    record "$name" "PASS"
  else
    record "$name" "FAIL"
  fi
}

# The environment CI uses for the test jobs (docs/operations/ci-cd.md §3.2).
ci_env() {
  env CLAIMSENSE_ENV=ci HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES="" TOKENIZERS_PARALLELISM=false "$@"
}

check_lock() {
  uv lock --check || return 1
  uv sync --frozen --all-extras || return 1
  uv export --frozen --all-extras --no-hashes > "$TMP_DIR/requirements-lock.txt" || return 1
  if ! diff -u requirements-lock.txt "$TMP_DIR/requirements-lock.txt"; then
    echo "requirements-lock.txt is out of date. Regenerate it with:"
    echo "  uv export --frozen --all-extras --no-hashes > requirements-lock.txt"
    return 1
  fi
}

check_test_count() {
  local floor count
  if [ ! -f "$FLOOR_FILE" ]; then
    echo "$FLOOR_FILE is missing"
    return 1
  fi
  floor="$(tr -d '[:space:]' < "$FLOOR_FILE")"
  count="$(uv run pytest --collect-only -q 2>/dev/null | grep -c '::')"
  echo "collected tests: $count (floor: $floor)"
  if [ "$count" -lt "$floor" ]; then
    echo "The collected test count dropped below the floor. Tests are never deleted."
    return 1
  fi
}

check_data() {
  # A skip is not a pass here (docs/testing/test-strategy.md §4).
  local log="$TMP_DIR/test-data.log"
  make test-data > "$log" 2>&1
  local rc=$?
  cat "$log"
  if grep -Eq 'no tests ran|[0-9]+ deselected' "$log" && ! grep -Eq '[0-9]+ (passed|failed|error)' "$log"; then
    echo "no local_data tests exist yet"
    return 0
  fi
  if [ "$rc" -ne 0 ]; then
    return 1
  fi
  if grep -Eq '[0-9]+ skipped' "$log"; then
    echo "local_data tests were skipped; a skip counts as a failure in pr-check"
    return 1
  fi
}

run_step "1 lock" check_lock
run_step "2 lint" make lint
run_step "3 test" ci_env make test
run_step "4 leak" ci_env make test-leak
run_step "5 e2e" ci_env make test-e2e
run_step "6 guard" bash scripts/ci_guard.sh
run_step "7 test count" check_test_count

DATA_ROOT="${CLAIMSENSE_DATA_DIR:-data}"
if [ -f "$DATA_ROOT/processed/LATEST" ]; then
  run_step "8 data" check_data
else
  echo
  echo "=== 8 data ==="
  echo "no $DATA_ROOT/processed/LATEST; local data checks not run"
  record "8 data" "PASS (no data, not run)"
fi

echo
echo "==================== pr-check summary ===================="
echo "| Check | Result |"
echo "|---|---|"
failed=0
i=0
while [ "$i" -lt "${#names[@]}" ]; do
  echo "| ${names[$i]} | ${results[$i]} |"
  case "${results[$i]}" in
    PASS*) ;;
    *) failed=1 ;;
  esac
  i=$((i + 1))
done
echo

if [ "$failed" -ne 0 ]; then
  echo "CHECKS FAILED"
  exit 1
fi
echo "ALL CHECKS PASSED"
