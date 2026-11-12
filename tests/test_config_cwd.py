"""La carga de configuración y los fixtures de test no deben depender del directorio actual."""

from pathlib import Path

from src.config import load_config


def test_load_config_default_path_independent_of_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = load_config()
    assert cfg.bertopic.embedding_model


def test_config_fixture_writes_only_to_tmp(config, tmp_path):
    for value in config.paths.model_dump().values():
        assert tmp_path in Path(value).parents
