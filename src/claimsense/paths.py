"""Where ClaimSense reads and writes files.

Base directories come from the ``paths`` section of the config and are relative
to the repo root. Two environment variables move them for Kaggle, Colab and
tests (configuration.md §5.2):

* ``CLAIMSENSE_DATA_DIR`` replaces the data directory.
* ``CLAIMSENSE_OUT_DIR`` replaces the repo root for everything that is written
  outside ``data/`` (models, index, reports).

These functions only compute paths; they never create directories.
"""

from __future__ import annotations

import os
from pathlib import Path

from claimsense import config as _config
from claimsense.config import Config
from claimsense.schema import SOURCES

DATA_DIR_ENV_VAR = "CLAIMSENSE_DATA_DIR"
OUT_DIR_ENV_VAR = "CLAIMSENSE_OUT_DIR"
LATEST_FILENAME = "LATEST"


def _cfg(cfg: Config | None) -> Config:
    return cfg if cfg is not None else _config.load()


def _env_dir(name: str) -> Path | None:
    value = os.environ.get(name)
    return Path(value).expanduser().resolve() if value else None


def _out_root() -> Path:
    return _env_dir(OUT_DIR_ENV_VAR) or _config.repo_root()


def data_dir(cfg: Config | None = None) -> Path:
    """Return the data directory: ``CLAIMSENSE_DATA_DIR`` if set, else ``paths.data_dir``."""
    return _env_dir(DATA_DIR_ENV_VAR) or _config.repo_root() / _cfg(cfg).paths.data_dir


def raw_dir(source: str, cfg: Config | None = None) -> Path:
    """Return ``<data>/raw/<source>``, the downloaded files of one source.

    Raises:
        ValueError: ``source`` is not one of ``claimsense.schema.SOURCES``.
    """
    if source not in SOURCES:
        raise ValueError(f"unknown source {source!r}; expected one of {SOURCES}")
    return data_dir(cfg) / "raw" / source


def interim_dir(cfg: Config | None = None) -> Path:
    """Return ``<data>/interim``, the extracted and segmented text."""
    return data_dir(cfg) / "interim"


def processed_root(cfg: Config | None = None) -> Path:
    """Return ``<data>/processed``, the parent of every dataset version."""
    return data_dir(cfg) / "processed"


def processed_dir(version: str, cfg: Config | None = None) -> Path:
    """Return the directory of one dataset version, ``<data>/processed/v<hash>``.

    A dataset version is ``"v"`` plus eight hex characters
    (dataset-versioning.md §1). The leading ``v`` may be given or left out; the
    hash is hexadecimal, so the two forms cannot be confused.
    """
    name = version if version.startswith("v") else f"v{version}"
    return processed_root(cfg) / name


def latest_processed(cfg: Config | None = None) -> Path | None:
    """Return the directory named in ``<data>/processed/LATEST``, or ``None`` if there is none."""
    pointer = processed_root(cfg) / LATEST_FILENAME
    if not pointer.is_file():
        return None
    return processed_dir(pointer.read_text(encoding="utf-8").strip(), cfg)


def models_dir(cfg: Config | None = None) -> Path:
    """Return the directory for model artefacts (adapter, calibrator, thresholds)."""
    return _out_root() / _cfg(cfg).paths.models_dir


def index_dir(cfg: Config | None = None) -> Path:
    """Return the directory of the precedent index."""
    return _out_root() / _cfg(cfg).paths.index_dir


def reports_dir(cfg: Config | None = None) -> Path:
    """Return the directory for generated reports."""
    return _out_root() / _cfg(cfg).paths.reports_dir
