"""The stages of the end-to-end chain (00-CONVENTIONS.md §7).

Each PR that adds a pipeline stage adds one ``run_<stage>(world)`` function
here and one ``test_e2e_NN_<stage>.py`` file that uses it. The pattern:

1. A stage function first calls the previous stage's function, so stage N
   always consumes the real output of stage N-1, never a hand-made fixture.
2. It then calls the **real public API** of its own stage. Only the network,
   LLMs and heavy models are replaced, by the stubs in ``tests/stubs/``,
   passed as constructor arguments.
3. It stores its result in ``world.cache`` under its own name and returns the
   cached value on later calls, so every stage runs once per session.
4. It reads and writes only inside ``world.root``. The world has already
   pointed ``CLAIMSENSE_DATA_DIR``, ``CLAIMSENSE_OUT_DIR`` and the config at
   that directory, so stage code uses ``claimsense.paths`` as usual.

Example for a later PR::

    def run_parse(world: E2EWorld) -> ParseResult:
        if "parse" not in world.cache:
            collected = run_collect(world)
            world.cache["parse"] = ...  # call the real parser on `collected`
        return world.cache["parse"]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from claimsense import config
from claimsense.config import Config

if TYPE_CHECKING:
    from tests.e2e.conftest import E2EWorld


def run_scaffold(world: E2EWorld) -> Config:
    """Stage 01: load the resolved config the way every later stage will."""
    if "scaffold" not in world.cache:
        world.cache["scaffold"] = config.load()
    return world.cache["scaffold"]
