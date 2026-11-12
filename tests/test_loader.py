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


def _mixed(make_db):
    return make_db(items=[{"repo": "a/b", "number": 1, "type": "issue"},
                          {"repo": "a/b", "number": 2, "type": "pr"},
                          {"repo": "a/b", "number": 3, "type": "discussion"}])


def test_default_item_types_yields_only_issues(make_db):
    items = list(load_items_sqlite(InputConfig(db_path=_mixed(make_db))))
    assert [(i.issue_number, i.item_type) for i in items] == [(1, "issue")]


def test_item_types_configurable(make_db):
    cfg = InputConfig(db_path=_mixed(make_db), item_types=["pr", "discussion"])
    assert sorted(i.item_type for i in load_items_sqlite(cfg)) == ["discussion", "pr"]


import json

from src.loader import LoadStats, RejectionRatioExceeded


def test_exclude_repos_skipped_and_counted(make_db):
    db = make_db(items=[{"repo": "x/Excluded", "number": 1}, {"repo": "a/b", "number": 1}])
    stats = LoadStats()
    items = list(load_items_sqlite(InputConfig(db_path=db, exclude_repos=["x/Excluded"]), stats))
    assert [i.repo for i in items] == ["a/b"]
    assert (stats.loaded, stats.excluded, stats.rejections.total) == (1, 1, 0)


def test_rejections_counted_and_written(make_db, tmp_path):
    db = make_db(items=[{"repo": "a/b", "number": 1},
                        {"repo": "a/b", "number": 2, "created_at": None},
                        {"repo": "a/b", "number": 3, "created_at": "not-a-date"},
                        {"repo": "", "number": 4}])
    stats, out = LoadStats(), tmp_path / "out" / "rejections.jsonl"
    cfg = InputConfig(db_path=db, max_reject_ratio=1.0)
    items = list(load_items_sqlite(cfg, stats, rejections_path=out))
    assert len(items) == 1 and stats.loaded == 1
    assert stats.rejections.by_reason == {"bad_created_at": 2, "missing_repo": 1}
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert sorted(r["reason"] for r in rows) == ["bad_created_at", "bad_created_at", "missing_repo"]


def test_reject_ratio_exceeded_fails_run(make_db):
    db = make_db(items=[{"repo": "a/b", "number": 1},
                        {"repo": "a/b", "number": 2, "created_at": None}])
    with pytest.raises(RejectionRatioExceeded):
        list(load_items_sqlite(InputConfig(db_path=db, max_reject_ratio=0.1), LoadStats()))


def test_reject_ratio_within_limit_passes(make_db):
    db = make_db(items=[{"repo": "a/b", "number": n} for n in range(1, 201)]
                 + [{"repo": "a/b", "number": 999, "created_at": None}])
    stats = LoadStats()
    list(load_items_sqlite(InputConfig(db_path=db, max_reject_ratio=0.01), stats))
    assert stats.rejections.total == 1
