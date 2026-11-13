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

import io
from dataclasses import dataclass
from typing import TYPE_CHECKING

from claimsense import config
from claimsense.collect.__main__ import main as collect_main
from claimsense.collect.manifest import Manifest, ManifestRow, manifest_path
from claimsense.collect.sources import SourceRegistry, load_registry
from claimsense.config import Config
from tests.e2e.corpus import Corpus, build_corpus
from tests.stubs.fake_clock import FakeClock
from tests.stubs.fake_http import FakeTransport

if TYPE_CHECKING:
    from tests.e2e.conftest import E2EWorld


def run_scaffold(world: E2EWorld) -> Config:
    """Stage 01: load the resolved config the way every later stage will."""
    if "scaffold" not in world.cache:
        world.cache["scaffold"] = config.load()
    return world.cache["scaffold"]


def run_sources(world: E2EWorld) -> SourceRegistry:
    """Stage 02: build the source registry from the world's config."""
    if "sources" not in world.cache:
        cfg = run_scaffold(world)
        world.cache["sources"] = load_registry(cfg)
    return world.cache["sources"]


@dataclass(frozen=True)
class CollectRun:
    """One run of the ``collect run`` command against a fake site."""

    source: str
    exit_code: int
    output: str
    requested_urls: tuple[str, ...]

    def count(self, name: str) -> int:
        """A number from the run's summary line, e.g. ``count("stored")``."""
        after = self.output.split(f"{name} ", 1)[1]
        return int(after.split(" ", 1)[0].replace(",", ""))


@dataclass(frozen=True)
class CollectResult:
    """What the collect stage produced: the first run of each source and the manifest rows."""

    runs: dict[str, CollectRun]
    rows: tuple[ManifestRow, ...]


def run_corpus(world: E2EWorld) -> Corpus:
    """Build the synthetic world's decisions and fake sites (once per session)."""
    if "corpus" not in world.cache:
        cfg = run_scaffold(world)
        world.cache["corpus"] = build_corpus(world.root / "sites", cfg.project.seed, cfg)
    return world.cache["corpus"]


def collect_once(world: E2EWorld, source: str) -> CollectRun:
    """Run the real ``collect run`` command for one source on its fake site. Not cached."""
    corpus = run_corpus(world)
    clock = FakeClock()
    transport = FakeTransport.from_urlmap(corpus.urlmaps[source], clock)
    out = io.StringIO()
    exit_code = collect_main(["run", "--source", source], transport=transport, clock=clock, out=out)
    return CollectRun(source, exit_code, out.getvalue(), tuple(transport.urls()))


def run_collect(world: E2EWorld, sources: tuple[str, ...] = ("cioins",)) -> CollectResult:
    """Stage 03: collect the world's sites into the manifest with the real collectors."""
    key = f"collect:{','.join(sources)}"
    if key not in world.cache:
        run_sources(world)
        runs = {source: collect_once(world, source) for source in sources}
        with Manifest(manifest_path(world.cfg)) as manifest:
            rows = tuple(manifest.rows())
        world.cache[key] = CollectResult(runs, rows)
    return world.cache[key]
