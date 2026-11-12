# ClaimSense: every routine command (docs/operations/setup.md §3.2).
# All targets run inside the project environment through `uv run`.

.PHONY: lint fmt test test-leak test-e2e test-data test-slow pr-check

# Tests never touch the network (docs/testing/test-strategy.md §1).
NET_BLOCK := --disable-socket --allow-unix-socket
# Extra pytest arguments, e.g. `make test PYTEST_ARGS="-x -k config"`.
PYTEST_ARGS ?=
# Until PR 6 adds the first leak probe, an empty leak run is allowed.
# PR 6 sets this to 0: from then on "no tests collected" is a failure.
LEAK_ALLOW_EMPTY ?= 1

lint:
	uv run ruff check .
	uv run black --check .

fmt:
	uv run ruff check --fix .
	uv run black .

test:
	uv run pytest -m "not slow and not local_data and not e2e" $(NET_BLOCK) $(PYTEST_ARGS)

test-leak:
	@uv run pytest tests/leak -m leak $(NET_BLOCK) $(PYTEST_ARGS); rc=$$?; \
	if [ $$rc -eq 5 ] && [ "$(LEAK_ALLOW_EMPTY)" = "1" ]; then \
		echo "no leak probes collected (allowed until PR 6)"; exit 0; \
	fi; exit $$rc

test-e2e:
	uv run pytest tests/e2e -m e2e $(NET_BLOCK) $(PYTEST_ARGS)

test-data:
	uv run pytest -m local_data -rs $(PYTEST_ARGS)

test-slow:
	uv run pytest -m slow $(PYTEST_ARGS)

pr-check:
	bash scripts/pr_check.sh
