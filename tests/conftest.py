"""Fixtures compartidas: configuración independiente del cwd, todas las salidas en tmp_path."""

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


ITEM_COLS = ["id", "repo", "number", "type", "title", "body", "state", "state_reason", "author",
             "author_type", "labels", "comment_count", "created_at", "closed_at", "merged_at",
             "complete", "assignees", "milestone", "draft", "category"]
COMMENT_COLS = ["id", "kind", "repo", "item_number", "author", "author_type", "created_at", "body"]


def _insert(conn, table, cols, row):
    full = {c: None for c in cols}
    full.update(row)
    conn.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                 [full[c] for c in cols])


@pytest.fixture
def make_db(tmp_path):
    """Crea un archivo SQLite pequeño con forma de miner.db; devuelve su ruta."""
    import sqlite3

    def build(items=(), comments=()):
        path = tmp_path / "miner.db"
        conn = sqlite3.connect(path)
        conn.execute(f"CREATE TABLE items ({','.join(ITEM_COLS)}, PRIMARY KEY (repo, number))")
        conn.execute(f"CREATE TABLE comments ({','.join(COMMENT_COLS)})")
        for n, row in enumerate(items, 1):
            _insert(conn, "items", ITEM_COLS, {"id": n, "type": "issue", "state": "open",
                                               "title": "t", "created_at": "2024-01-01T00:00:00Z",
                                               "labels": "[]", "assignees": "[]", **row})
        for n, row in enumerate(comments, 1):
            _insert(conn, "comments", COMMENT_COLS, {"id": n, "kind": "issue_comment",
                                                     "created_at": "2024-01-02T00:00:00Z", **row})
        conn.commit()
        conn.close()
        return path

    return build
