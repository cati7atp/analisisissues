"""Metrics correctness."""

import json
import math
from datetime import datetime

import pytest

from src.metrics import compute_topic_entropy, get_top_topics_for_repo, compute_aggregated_metrics
from src.models import CleanedIssue, RepoMetrics


def _issue(repo, n, **kw):
    return CleanedIssue(repo=repo, issue_number=n, title="t", cleaned_body="", state="open",
                        created_at=datetime(2024, 1, 1), author="u", full_text="t", **kw)


def _doc_topics(tmp_path, assignments):
    path = tmp_path / "doc_topics.jsonl"
    path.write_text("\n".join(json.dumps({"issue_id": i, "topic_id": t, "probability": 1.0})
                              for i, t in assignments.items()) + "\n", encoding="utf-8")
    return path


def test_entropy_uses_each_repos_own_topic_distribution(tmp_path):
    a = [_issue("a/a", n) for n in range(4)]
    b = [_issue("b/b", n) for n in range(4)]
    path = _doc_topics(tmp_path, {**{i.issue_id: 0 for i in a},
                                  **{b[0].issue_id: 1, b[1].issue_id: 1, b[2].issue_id: 2, b[3].issue_id: 2}})
    assert compute_topic_entropy(a, path) == 0.0
    assert compute_topic_entropy(b, path) == pytest.approx(1.0)


def test_topic_zero_is_a_valid_topic(tmp_path):
    issues = [_issue("a/a", n) for n in range(3)]
    path = _doc_topics(tmp_path, {i.issue_id: 0 for i in issues})
    assert get_top_topics_for_repo(issues, path) == [{"topic_id": 0, "count": 3, "percentage": 100.0}]


def test_zero_median_resolution_is_valid_in_aggregates():
    def rm(repo, median):
        return RepoMetrics(repo=repo, total_issues=2, open_issues=0, closed_issues=2, issue_types={},
                           median_resolution_days=median)
    agg = compute_aggregated_metrics([rm("a/a", 0.0), rm("b/b", 0.0), rm("c/c", 10.0)], [], [])
    assert agg.overall_median_resolution_days == 0.0


def test_parse_datetime_returns_utc_aware_values():
    from datetime import timedelta, timezone
    from src.models import parse_datetime

    for text in ["2024-01-01T10:00:00Z", "2024-01-01T10:00:00.5Z", "2024-01-01T10:00:00", "2024-01-01T12:00:00+02:00"]:
        dt = parse_datetime(text)
        assert dt.utcoffset() == timedelta(0) and dt.tzinfo is not None, text
    assert parse_datetime("2024-01-01T12:00:00+02:00") == datetime(2024, 1, 1, 10, tzinfo=timezone.utc)


def test_resolution_time_handles_mixed_naive_and_aware_input():
    from datetime import timezone
    from src.metrics import compute_resolution_time

    naive_created = _issue("a/a", 1)  # created 2024-01-01 naive
    naive_created.closed_at = datetime(2024, 1, 3, tzinfo=timezone.utc)
    assert compute_resolution_time(naive_created) == pytest.approx(2.0)
    missing = _issue("a/a", 2)
    assert compute_resolution_time(missing) is None


def test_unparseable_dates_become_none_and_are_counted_never_now(config):
    from src.models import RawIssue
    from src.preprocess import IssuePreprocessor

    pre = IssuePreprocessor(config)
    base = dict(repo="a/b", issue_number=1, title="Circuit depth grows after transpile",
                body="The transpiled circuit is much deeper than expected.", state="closed", author="u")
    cleaned = pre.clean_issue(RawIssue(**base, created_at="2024-01-01T00:00:00Z", closed_at="garbage"))
    assert cleaned.closed_at is None and pre.datetime_failures == 1
    assert pre.clean_issue(RawIssue(**base, created_at="garbage")) is None
    assert pre.last_skip_reason == "bad_created_at" and pre.datetime_failures == 2
