"""SQLite loader for miner.db."""

import pytest

from src.config import InputConfig
from src.loader import load_items_sqlite


def test_input_config_defaults():
    cfg = InputConfig(db_path="x.db")
    assert cfg.item_types == ["issue"]
    assert cfg.include_comment_kinds == ["issue_comment"]
    assert cfg.max_reject_ratio == 0.005


def test_loads_items_with_mapped_fields(make_db):
    db = make_db(items=[{"repo": "a/b", "number": 7, "title": "Hello", "body": "World",
                         "author": "u", "state": "closed"}])
    items = list(load_items_sqlite(InputConfig(db_path=db)))
    assert len(items) == 1
    it = items[0]
    assert (it.repo, it.issue_number, it.title, it.body, it.author, it.state) == \
        ("a/b", 7, "Hello", "World", "u", "closed")


def test_loader_is_a_generator(make_db):
    db = make_db(items=[{"repo": "a/b", "number": 1}])
    assert iter(g := load_items_sqlite(InputConfig(db_path=db))) is g


def test_db_opened_read_only(make_db, tmp_path):
    missing = tmp_path / "nope.db"
    with pytest.raises(Exception):
        list(load_items_sqlite(InputConfig(db_path=missing)))
    assert not missing.exists()
    db = make_db(items=[{"repo": "a/b", "number": 1}])
    before = db.read_bytes()
    list(load_items_sqlite(InputConfig(db_path=db)))
    assert db.read_bytes() == before
