"""Tests for the corpus-level repeated-line and repeated-comment filters (S12)."""

import json

import pytest

from src.models import RawIssue
from src.preprocess import IssuePreprocessor

def UNIQUE(i):
    return "w" + "x" * i + "z"


FOOTER = "Sent from my build runner automatic footer"
SUMMARY = "```\nTraceback (most recent call last):\n  File \"a.py\", line 1, in f\n    x()\nQiskitError: boom happened\n```"


def _issue(n, body, comments=()):
    return RawIssue(
        repo="a/b", issue_number=n, title="Same title in every issue", body=body, state="open",
        labels=[], created_at="2024-01-01T00:00:00Z", author="human",
        comments=[{"author": "helper", "created_at": "2024-01-02T00:00:00Z", "body": c} for c in comments],
    )


def _run(config, issues, tmp_path):
    out = tmp_path / "clean.jsonl"
    stats = IssuePreprocessor(config).process_items(lambda: iter(issues), out)
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()]
    return stats, rows


def _bodies(n_footer, total):
    return [
        _issue(i, f"Unique problem description {UNIQUE(i)} with details.\n{FOOTER}" if i < n_footer
               else f"Unique problem description {UNIQUE(i)} with details.")
        for i in range(total)
    ]


def test_line_repeated_in_20_issues_is_removed_and_unique_line_kept(config, tmp_path):
    stats, rows = _run(config, _bodies(20, 25), tmp_path)
    assert all("automatic footer" not in r["full_text"] for r in rows)
    assert all("Unique problem description" in r["cleaned_body"] for r in rows)
    assert stats["repeated_lines"] == 1
    assert stats["repeated_line_removals"] == 20


def test_line_repeated_in_19_issues_is_kept(config, tmp_path):
    stats, rows = _run(config, _bodies(19, 25), tmp_path)
    assert sum("automatic footer" in r["cleaned_body"] for r in rows) == 19
    assert stats["repeated_lines"] == 0


def test_repetition_inside_one_issue_counts_once(config, tmp_path):
    issues = [_issue(i, "\n".join([FOOTER] * 30) + f"\nReal text {UNIQUE(i)} for the maintainers.") for i in range(5)]
    _, rows = _run(config, issues, tmp_path)
    assert all("automatic footer" in r["cleaned_body"] for r in rows)


def test_exception_summary_is_never_removed_by_the_line_filter(config, tmp_path):
    issues = [_issue(i, f"Crash number {i} in my notebook.\n{SUMMARY}") for i in range(25)]
    _, rows = _run(config, issues, tmp_path)
    assert all("QiskitError: boom happened" in r["cleaned_body"] for r in rows)


def test_titles_are_never_filtered(config, tmp_path):
    _, rows = _run(config, _bodies(25, 25), tmp_path)
    assert all(r["title"] == "Same title in every issue" for r in rows)
    assert all("Same title in every issue" in r["full_text"] for r in rows)


def test_plain_iterable_still_works_without_the_filter(config, tmp_path):
    out = tmp_path / "clean.jsonl"
    stats = IssuePreprocessor(config).process_items(iter(_bodies(25, 25)), out)
    assert stats["kept"] == 25
    assert "repeated_lines" not in stats or stats["repeated_lines"] == 0


def test_threshold_zero_disables_the_filter(config, tmp_path):
    config.preprocessing.repeated_line_min_issues = 0
    _, rows = _run(config, _bodies(25, 25), tmp_path)
    assert all("automatic footer" in r["cleaned_body"] for r in rows)


def test_cli_preprocess_uses_two_passes_without_double_counting(make_db, tmp_path):
    from tests.test_cli_preprocess import _config, runner
    from src.cli import app

    items = [{"repo": "a/b", "number": i, "title": f"Title {UNIQUE(i)}", "author": "u",
              "body": f"Real description {UNIQUE(i)} of the problem.\n{FOOTER}"} for i in range(1, 23)]
    cfg = _config(tmp_path, make_db(items=items))
    result = runner.invoke(app, ["preprocess", "--config", str(cfg)])
    assert result.exit_code == 0, result.output
    assert "loaded: 22" in result.output
    assert "repeated lines: 1 distinct, 22 removed" in result.output
    rows = [json.loads(l) for l in (tmp_path / "out" / "issues_clean.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 22 and all("automatic footer" not in r["cleaned_body"] for r in rows)


def _with_comment(n_issues, comment, total=25):
    return [_issue(i, f"Description {UNIQUE(i)} of the problem.", [comment] if i < n_issues else [f"A human reply {UNIQUE(i)}"]) for i in range(total)]


AUTOMATED = "Release notes: registered a new version through the registry bot"


def test_comment_seen_in_5_issues_is_dropped(config, tmp_path):
    stats, rows = _run(config, _with_comment(5, AUTOMATED), tmp_path)
    assert all("registry bot" not in r["full_text"] for r in rows)
    assert stats["repeated_comments"] == 1
    assert stats["repeated_comment_drops"] == 5
    assert len(rows) == 25  # the issues themselves are kept


def test_comment_seen_in_4_issues_is_kept(config, tmp_path):
    stats, rows = _run(config, _with_comment(4, AUTOMATED), tmp_path)
    assert sum("registry bot" in r["full_text"] for r in rows) == 4
    assert stats["repeated_comments"] == 0


def test_comment_repeated_inside_one_issue_counts_once(config, tmp_path):
    issues = [_issue(i, f"Description {UNIQUE(i)} of the problem.", [AUTOMATED + " v1", AUTOMATED + " v1"]) for i in range(3)]
    _, rows = _run(config, issues, tmp_path)
    assert all("registry bot" in r["full_text"] for r in rows)


def test_repeated_exception_summary_comment_is_kept(config, tmp_path):
    _, rows = _run(config, _with_comment(10, SUMMARY), tmp_path)
    assert sum("QiskitError: boom happened" in r["full_text"] for r in rows) == 10


def test_comment_threshold_zero_disables_the_comment_filter(config, tmp_path):
    config.preprocessing.repeated_comment_min_issues = 0
    _, rows = _run(config, _with_comment(10, AUTOMATED), tmp_path)
    assert sum("registry bot" in r["full_text"] for r in rows) == 10
