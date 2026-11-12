"""The e2e world (00-CONVENTIONS.md §7): a temp root, env overrides and a stage cache."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import yaml

from claimsense import config, paths
from claimsense.config import Config

E2E_CONFIG = Path(__file__).parent / "e2e_config.yaml"


@dataclass
class E2EWorld:
    """Everything the e2e stages share during one test session.

    Attributes:
        root: Temp directory that contains every file the stages read or write.
        cfg: The resolved config: ``config.yaml`` merged with ``e2e_config.yaml``,
            with every path pointing inside ``root``.
        env: The environment variables the world set for the session.
        cache: Stage outputs, keyed by stage name, so each stage runs once.
    """

    root: Path
    cfg: Config
    env: dict[str, str]
    cache: dict[str, Any] = field(default_factory=dict)


def _world_paths(base_paths: dict[str, str], data: Path, out: Path) -> dict[str, str]:
    """Move every ``paths.*`` key inside the world, keeping its layout."""
    base_data = Path(base_paths["data_dir"])
    moved: dict[str, str] = {}
    for key, value in base_paths.items():
        relative = Path(value)
        if relative == base_data or base_data in relative.parents:
            moved[key] = str(data / relative.relative_to(base_data))
        else:
            moved[key] = str(out / relative)
    return moved


@pytest.fixture(scope="session")
def world(tmp_path_factory: pytest.TempPathFactory) -> Iterator[E2EWorld]:
    """Build the session's world and point ClaimSense at it through the environment."""
    root = tmp_path_factory.mktemp("e2e_world").resolve()
    data, out, mlruns = root / "data", root / "out", root / "mlruns"
    for directory in (data, out, mlruns):
        directory.mkdir()

    base = yaml.safe_load((config.repo_root() / config.CONFIG_FILENAME).read_text("utf-8"))
    override = yaml.safe_load(E2E_CONFIG.read_text("utf-8")) or {}
    merged = config.deep_merge(base, override)
    merged["paths"] = _world_paths(merged["paths"], data, out)
    world_config = root / "config.yaml"
    world_config.write_text(yaml.safe_dump(merged, sort_keys=False), encoding="utf-8")

    env = {
        paths.DATA_DIR_ENV_VAR: str(data),
        paths.OUT_DIR_ENV_VAR: str(out),
        config.OVERRIDE_ENV_VAR: str(world_config),
        "CLAIMSENSE_ENV": "ci",
        "MLFLOW_TRACKING_URI": mlruns.as_uri(),
    }
    patcher = pytest.MonkeyPatch()
    for name, value in env.items():
        patcher.setenv(name, value)
    try:
        yield E2EWorld(root=root, cfg=config.load(), env=env)
    finally:
        patcher.undo()
