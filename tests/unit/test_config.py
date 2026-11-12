"""Config loader (NFR-05a; configuration.md §1-§2, §7): validation, override merge, hash, CLI."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from claimsense import config

pytestmark = pytest.mark.usefixtures("clean_env")

SECRET_WORDS = ("key", "token", "secret")


def _base_data() -> dict[str, Any]:
    """The committed config.yaml as plain data."""
    return yaml.safe_load((config.repo_root() / config.CONFIG_FILENAME).read_text(encoding="utf-8"))


def _write_yaml(path: Path, data: dict[str, Any]) -> Path:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def _walk(data: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    """Yield (dotted key, value) for every key at every depth."""
    if isinstance(data, dict):
        for key, value in data.items():
            dotted = f"{prefix}.{key}" if prefix else str(key)
            yield dotted, value
            yield from _walk(value, dotted)
    elif isinstance(data, list):
        for item in data:
            yield from _walk(item, prefix)


def test_loads_and_validates() -> None:
    cfg = config.load()
    assert cfg.project.name == "claimsense"


def test_unknown_key_rejected(tmp_path: Path) -> None:
    data = _base_data()
    data["project"]["colour"] = "red"
    with pytest.raises(ValidationError, match="colour"):
        config.load(_write_yaml(tmp_path / "config.yaml", data))


def test_override_merge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = config.load()
    new_seed = base.project.seed + 1
    override = _write_yaml(tmp_path / "override.yaml", {"project": {"seed": new_seed}})
    monkeypatch.setenv(config.OVERRIDE_ENV_VAR, str(override))

    merged = config.load()

    assert merged.project.seed == new_seed
    expected = base.model_dump()
    expected["project"]["seed"] = new_seed
    assert merged.model_dump() == expected


def test_no_secrets() -> None:
    resolved = config.load().model_dump(mode="json")
    for dotted, value in _walk(resolved):
        name = dotted.rsplit(".", 1)[-1].lower()
        if any(word in name for word in SECRET_WORDS):
            assert value in ("", None), f"{dotted} looks like a secret and must be empty"


def test_config_hash_stable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = config.load()
    assert config.config_hash(base) == config.config_hash(config.load())

    # project.seed is tagged runtime-only (configuration.md §3.1), so it is not hashed.
    assert "project.seed" not in config.V_KEYS
    override = _write_yaml(tmp_path / "override.yaml", {"project": {"seed": base.project.seed + 1}})
    monkeypatch.setenv(config.OVERRIDE_ENV_VAR, str(override))
    changed = config.load()
    assert changed != base
    assert config.config_hash(changed) == config.config_hash(base)


def test_cli_check_exit_codes(tmp_path: Path) -> None:
    command = [sys.executable, "-m", "claimsense.config", "check"]
    env = {k: v for k, v in os.environ.items() if k != config.OVERRIDE_ENV_VAR}

    ok = subprocess.run(command, env=env, capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr

    broken = _write_yaml(tmp_path / "broken.yaml", {"project": {"colour": "red"}})
    bad = subprocess.run(
        command, env={**env, config.OVERRIDE_ENV_VAR: str(broken)}, capture_output=True, text=True
    )
    assert bad.returncode == 1
    assert "colour" in bad.stderr
