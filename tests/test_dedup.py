"""Tests for exact duplicate document removal (S12)."""

import json

from src.models import RawIssue
from src.preprocess import IssuePreprocessor

BODY = "The optimizer does not converge on real hardware after many iterations."


def _issue(n, title="VQE does not converge", body=BODY, repo="a/b"):
    return RawIssue(repo=repo, issue_number=n, title=title, body=body, state="open", labels=[],
                    created_at="2024-01-01T00:00:00Z", author="human")


def _run(config, issues, tmp_path):
    out = tmp_path / "clean.jsonl"
    stats = IssuePreprocessor(config).process_items(iter(issues), out)
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()]
    return stats, rows


def test_exact_duplicate_is_dropped_and_first_occurrence_kept(config, tmp_path):
    issues = [_issue(1), _issue(2, title="VQE  does not CONVERGE", body=BODY.upper() + "  "), _issue(3)]
    stats, rows = _run(config, issues, tmp_path)
    assert [r["issue_number"] for r in rows] == [1]
    assert stats["duplicates"] == 2
    assert stats["skipped"] == 2


def test_same_text_in_another_repo_is_a_duplicate(config, tmp_path):
    stats, rows = _run(config, [_issue(1), _issue(1, repo="c/d")], tmp_path)
    assert len(rows) == 1 and stats["duplicates"] == 1


def test_different_title_or_body_is_kept(config, tmp_path):
    issues = [_issue(1), _issue(2, title="Another title"), _issue(3, body=BODY + " Extra detail here.")]
    stats, rows = _run(config, issues, tmp_path)
    assert len(rows) == 3 and stats["duplicates"] == 0


def test_dedup_can_be_disabled(config, tmp_path):
    config.preprocessing.drop_exact_duplicates = False
    stats, rows = _run(config, [_issue(1), _issue(2)], tmp_path)
    assert len(rows) == 2 and stats["duplicates"] == 0


def test_duplicates_are_reported_by_the_cli(make_db, tmp_path):
    from tests.test_cli_preprocess import _config, runner
    from src.cli import app

    items = [{"repo": "a/b", "number": n, "title": "Same", "body": BODY, "author": "u"} for n in (1, 2)]
    result = runner.invoke(app, ["preprocess", "--config", str(_config(tmp_path, make_db(items=items)))])
    assert result.exit_code == 0, result.output
    assert "skipped (exact duplicates): 1" in result.output
    assert "skipped (empty content): 0" in result.output
