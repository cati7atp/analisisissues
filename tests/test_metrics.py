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


def _write_issues(path, issues):
    with open(path, "w", encoding="utf-8") as f:
        for issue in issues:
            data = issue.model_dump()
            data["created_at"] = issue.created_at.isoformat()
            data["closed_at"] = issue.closed_at.isoformat() if issue.closed_at else None
            f.write(json.dumps(data, ensure_ascii=False) + "\n")


def _run_metrics(config, tmp_path, issues, assignments=None):
    from src.metrics import compute_maintainability_metrics

    issues_file = tmp_path / "issues.jsonl"
    _write_issues(issues_file, issues)
    config.paths.doc_topics_output.parent.mkdir(parents=True, exist_ok=True)
    config.paths.doc_topics_output.write_text("\n".join(
        json.dumps({"issue_id": i.issue_id, "topic_id": (assignments or {}).get(i.issue_id, 0), "probability": 1.0},
                   ensure_ascii=False) for i in issues) + "\n", encoding="utf-8")
    patterns = tmp_path / "patterns.jsonl"
    patterns.write_text("", encoding="utf-8")
    return compute_maintainability_metrics(config, issues_file, patterns, tmp_path / "m.json", tmp_path / "m.csv")


def test_reopen_rate_and_label_churn_are_gone_from_outputs(config, tmp_path):
    result = _run_metrics(config, tmp_path, [_issue("a/a", 1), _issue("b/b", 1)])
    dumped = json.loads((tmp_path / "m.json").read_text(encoding="utf-8"))
    assert "reopen_rate" not in dumped["per_repo"][0] and "label_churn_per_issue" not in dumped["per_repo"][0]
    assert "overall_reopen_rate" not in dumped["aggregated"]
    assert "reopen_rate" not in (tmp_path / "m.csv").read_text(encoding="utf-8")
    assert result.aggregated.total_issues == 2


def test_state_reason_resolution_outcome_breakdown(config, tmp_path):
    from datetime import timezone

    closed = datetime(2024, 1, 2, tzinfo=timezone.utc)
    issues = []
    for n, reason in enumerate(["completed", "completed", "not_planned", "duplicate", None]):
        issue = _issue("a/a", n, state_reason=reason)
        issue.state, issue.closed_at = "closed", closed
        issues.append(issue)
    issues.append(_issue("a/a", 99, state_reason="reopened"))  # open: not an outcome
    result = _run_metrics(config, tmp_path, issues)
    expected = {"completed": 2, "not_planned": 1, "duplicate": 1, "unspecified": 1}
    assert result.per_repo[0].resolution_outcomes == expected
    assert result.aggregated.resolution_outcomes == expected


def test_overall_gini_is_computed_on_pooled_authors(config, tmp_path):
    from src.metrics import compute_contributor_gini

    issues = [_issue("a/a", n) for n in range(4)]  # one author, 4 issues
    for n, name in enumerate("pqrs"):
        issue = _issue("b/b", n)
        issue.author = name
        issues.append(issue)
    result = _run_metrics(config, tmp_path, issues)
    assert result.aggregated.overall_gini_contributors == pytest.approx(compute_contributor_gini(issues))
    assert result.aggregated.overall_gini_contributors > 0.0  # the mean of the repo Ginis is 0


def test_doc_topics_read_once_as_utf8(config, tmp_path, monkeypatch):
    import src.metrics as metrics

    reads = []
    original = metrics.load_doc_topic_map
    monkeypatch.setattr(metrics, "load_doc_topic_map", lambda p: reads.append(p) or original(p))
    issues = [_issue("ünï/çödé", 1), _issue("b/b", 1)]
    result = _run_metrics(config, tmp_path, issues)
    assert len(reads) == 1
    assert result.per_repo[0].top_topics == [{"topic_id": 0, "count": 1, "percentage": 100.0}]
