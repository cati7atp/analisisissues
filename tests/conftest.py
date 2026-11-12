"""Shared fixtures: config independent of cwd, all outputs under tmp_path."""

from pathlib import Path

import pytest

from src.config import load_config

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def config(tmp_path):
    cfg = load_config(REPO_ROOT / "config.yaml")
    for name, value in cfg.paths.model_dump().items():
        setattr(cfg.paths, name, tmp_path / value)
    return cfg
