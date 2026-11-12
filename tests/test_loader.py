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


def test_comments_joined_by_repo_and_number(make_db):
    db = make_db(
        items=[{"repo": "a/b", "number": 1}, {"repo": "a/c", "number": 1}],
        comments=[
            {"repo": "a/b", "item_number": 1, "author": "u1", "body": "first", "author_type": "User"},
            {"repo": "a/c", "item_number": 1, "author": "u2", "body": "other repo"},
            {"repo": "a/b", "item_number": 1, "kind": "review_comment", "author": "u3", "body": "skip"},
        ],
    )
    items = {i.repo: i for i in load_items_sqlite(InputConfig(db_path=db))}
    assert [(c.author, c.body, c.kind, c.author_type) for c in items["a/b"].comments] == \
        [("u1", "first", "issue_comment", "User")]
    assert [c.body for c in items["a/c"].comments] == ["other repo"]


def test_labels_and_assignees_parsed_from_json(make_db):
    db = make_db(items=[{"repo": "a/b", "number": 1, "labels": '["bug", "prio: high"]',
                         "assignees": '["alice"]', "state_reason": "completed",
                         "author_type": "Bot", "comment_count": 3, "merged_at": None}])
    it = next(load_items_sqlite(InputConfig(db_path=db)))
    assert it.labels == ["bug", "prio: high"]
    assert it.assignees == ["alice"]
    assert (it.state_reason, it.author_type, it.comment_count, it.item_type) == \
        ("completed", "Bot", 3, "issue")
