"""Load, validate and hash the ClaimSense configuration.

``config.yaml`` is the one source of truth for every threshold, seed, path and
model ID (docs/operations/configuration.md). This module parses it into a
Pydantic model, so unknown keys and wrong types fail at start-up.

Load order (configuration.md §2)::

    config.yaml  ->  file named in CLAIMSENSE_CONFIG (deep-merged, optional)

Command line::

    python -m claimsense.config show [--section X]   # print the resolved config
    python -m claimsense.config check                # validate only; exit 1 on error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

CONFIG_FILENAME = "config.yaml"
OVERRIDE_ENV_VAR = "CLAIMSENSE_CONFIG"

# Registry of the keys tagged **V** in configuration.md §3: the keys that are
# part of the dataset ``config_hash``. Each entry is a dotted path into the
# resolved config and may name a single key or a whole section. The PR that
# adds a V key to the schema adds it here. No V key exists yet.
V_KEYS: tuple[str, ...] = ()


class ConfigError(ValueError):
    """A config file is missing, unreadable or not a YAML mapping."""


class _Section(BaseModel):
    """Base for every config section: unknown keys are errors, values are frozen."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ProjectConfig(_Section):
    """The ``project`` section (configuration.md §3.1)."""

    name: str
    version: str
    seed: int
    seeds: tuple[int, ...]


class PathsConfig(_Section):
    """The ``paths`` section (configuration.md §3.1); resolved by ``claimsense.paths``."""

    data_dir: Path
    models_dir: Path
    index_dir: Path
    reports_dir: Path
    cache_dir: Path


class Config(_Section):
    """The whole resolved configuration."""

    project: ProjectConfig
    paths: PathsConfig


def repo_root() -> Path:
    """Return the directory that holds ``config.yaml``.

    This is the repository root for a checkout or an editable install. If the
    package is installed elsewhere (for example in a notebook), the current
    working directory is used instead.
    """
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / CONFIG_FILENAME).is_file():
        return candidate
    return Path.cwd()


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Return ``base`` with ``override`` merged on top, without changing either.

    Mappings are merged key by key at every depth; any other value (including a
    list) in ``override`` replaces the value in ``base``.
    """
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _read_yaml(path: Path) -> dict[str, Any]:
    """Read one YAML file as a mapping; an empty file is an empty mapping."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read config file {path}: {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} is not valid YAML: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a YAML mapping, got {type(data).__name__}")
    return data


def _override_path() -> Path | None:
    """Return the override file named in ``CLAIMSENSE_CONFIG``, if the variable is set."""
    value = os.environ.get(OVERRIDE_ENV_VAR)
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute() and not path.exists():
        path = repo_root() / path
    return path


def load(path: Path | None = None) -> Config:
    """Load and validate the resolved configuration.

    Args:
        path: Base config file. Defaults to ``config.yaml`` in the repo root.

    Returns:
        The validated config, after deep-merging the file named in
        ``CLAIMSENSE_CONFIG`` (if set) on top of the base file.

    Raises:
        ConfigError: A file is missing, unreadable or not a YAML mapping.
        pydantic.ValidationError: A key is unknown, missing or of the wrong type.
    """
    base_path = Path(path) if path is not None else repo_root() / CONFIG_FILENAME
    data = _read_yaml(base_path)
    override = _override_path()
    if override is not None:
        data = deep_merge(data, _read_yaml(override))
    return Config.model_validate(data)


def _lookup(data: Mapping[str, Any], dotted_key: str) -> Any:
    """Return the value at a dotted path, e.g. ``dataset.split.train_end``."""
    value: Any = data
    for part in dotted_key.split("."):
        if not isinstance(value, Mapping) or part not in value:
            raise KeyError(f"config key {dotted_key!r} is in V_KEYS but not in the config")
        value = value[part]
    return value


def config_hash(cfg: Config) -> str:
    """Return the SHA-256 of the canonical JSON of the keys tagged **V**.

    Only the keys listed in ``V_KEYS`` are hashed, so changing a runtime-only
    key never changes the hash, and changing a V key always does
    (configuration.md §1 rule 5, dataset-versioning.md §2).
    """
    resolved = cfg.model_dump(mode="json")
    selected = {key: _lookup(resolved, key) for key in sorted(V_KEYS)}
    canonical = json.dumps(selected, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m claimsense.config",
        description="Show or validate the resolved ClaimSense configuration.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    show = commands.add_parser("show", help="print the resolved config as YAML")
    show.add_argument("--section", help="print only this top-level section")
    commands.add_parser("check", help="validate only; exit 1 on error")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``show`` / ``check`` command line and return its exit code."""
    args = _build_parser().parse_args(argv)
    try:
        cfg = load()
    except (ConfigError, ValidationError) as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 1

    if args.command == "check":
        print("config OK")
        return 0

    resolved = cfg.model_dump(mode="json")
    if args.section is not None:
        if args.section not in resolved:
            known = ", ".join(resolved)
            print(f"unknown section {args.section!r}; sections: {known}", file=sys.stderr)
            return 1
        resolved = {args.section: resolved[args.section]}
    yaml.safe_dump(resolved, sys.stdout, sort_keys=False, allow_unicode=True, width=float("inf"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
