"""Cross-project patterns: a topic that recurs in several distinct repos."""

import json

import pytest
from datetime import datetime

from src.cross_project import find_cross_project_topics, write_cross_project_outputs
from src.models import CleanedIssue, DocTopic, TopicInfo


def _issue(repo, n):
    return CleanedIssue(repo=repo, issue_number=n, title=f"t{n}", cleaned_body="", state="open",
                        created_at=datetime(2024, 1, 1), author="u", full_text="x")


def _topic(tid, repo_specific=False):
    return TopicInfo(topic_id=tid, name=f"{tid}_a_b", keywords=["a", "b"], count=1, repo_specific=repo_specific)


def _world():
    issues, dts = [], []

    def add(repo, n, topic):
        issues.append(_issue(repo, n))
        dts.append(DocTopic(issue_id=f"{repo}#{n}", topic_id=topic, probability=1.0))

    for r in ("a/x", "b/y", "c/z"):          # topic 0: 3 issues in each of 3 repos -> cross-project
        for n in range(3):
            add(r, n, 0)
    for n in range(20):                      # topic 1: huge repo plus one stray issue -> not cross-project
        add("a/x", 100 + n, 1)
    add("b/y", 100, 1)
    for n in range(5):                       # topic 2: flagged repo_specific upstream
        add("a/x", 200 + n, 2)
    add("a/x", 300, -1)                      # outlier is never a topic
    return issues, dts, [_topic(0), _topic(1), _topic(2, repo_specific=True)]


def _by_id(rows):
    return {r["topic_id"]: r for r in rows}


def test_topic_spread_over_enough_repos_is_cross_project():
    issues, dts, topics = _world()
    rows = _by_id(find_cross_project_topics(topics, dts, issues, min_repos=3, min_issues_per_repo=3, max_top_repo_share=0.8))
    row = rows[0]
    assert row["cross_project"] is True
    assert row["n_repos"] == 3 and row["supporting_repos"] == ["a/x", "b/y", "c/z"]
    assert row["n_issues"] == 9 and row["top_repo_share"] == 1 / 3
    assert row["evenness"] == pytest.approx(1.0)
    assert row["per_repo"]["a/x"] == {"n": 3, "prevalence": 3 / 29}


def test_dominated_or_thin_topics_are_not_cross_project():
    issues, dts, topics = _world()
    rows = _by_id(find_cross_project_topics(topics, dts, issues, min_repos=3, min_issues_per_repo=3, max_top_repo_share=0.8))
    assert rows[1]["cross_project"] is False      # only one repo reaches min_issues_per_repo
    assert rows[1]["supporting_repos"] == ["a/x"]


def test_single_repo_topic_is_not_cross_project_and_outliers_are_skipped():
    issues, dts, topics = _world()
    rows = _by_id(find_cross_project_topics(topics, dts, issues, min_repos=2, min_issues_per_repo=1, max_top_repo_share=1.0))
    assert rows[2]["cross_project"] is False and rows[2]["repo_specific"] is True
    assert -1 not in rows


def test_dominant_repo_alone_does_not_hide_a_topic_that_recurs_elsewhere():
    issues, dts, topics = _world()
    topics[0].repo_specific = True  # flagged by the stricter upstream threshold
    rows = _by_id(find_cross_project_topics(topics, dts, issues, min_repos=3, min_issues_per_repo=3, max_top_repo_share=0.9))
    assert rows[0]["cross_project"] is True


def test_outputs_are_written_as_jsonl_and_csv(tmp_path):
    issues, dts, topics = _world()
    rows = find_cross_project_topics(topics, dts, issues, min_repos=3, min_issues_per_repo=3, max_top_repo_share=0.8)
    write_cross_project_outputs(rows, tmp_path / "cross_project_patterns.jsonl", tmp_path / "cross_project_patterns.csv")
    lines = (tmp_path / "cross_project_patterns.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3 and json.loads(lines[0])["topic_id"] == 0
    csv = (tmp_path / "cross_project_patterns.csv").read_text(encoding="utf-8").splitlines()
    assert csv[0].startswith("topic_id,name") and len(csv) == 4
