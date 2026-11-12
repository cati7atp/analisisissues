"""Cross-repo comparison views control for repo imbalance (S24)."""

import sqlite3
from datetime import datetime

import pytest

from src.comparisons import compare_groups, load_repo_families
from src.models import CleanedIssue
from src.taxonomy import TaxonomyMatcher, load_taxonomy


def _issue(repo, n, text):
    return CleanedIssue(repo=repo, issue_number=n, title=text, cleaned_body="", state="open",
                        created_at=datetime(2024, 1, 1), author="u", full_text=text)


@pytest.fixture
def matcher(config):
    return TaxonomyMatcher(load_taxonomy(config.quantum_taxonomy))


def _corpus():
    big = [_issue("big/sdk", n, "transpile fails" if n % 2 else "tea recipe") for n in range(100)]
    small = [_issue("small/lib", n, "pulse schedule broken") for n in range(4)]
    return big + small


def test_views_per_repo_and_family_report_pattern_and_topic_shares(matcher):
    issues = _corpus()
    topics = {i.issue_id: (0 if i.repo == "big/sdk" else 1) for i in issues}
    families = {"big/sdk": ["Compilers"], "small/lib": ["Compilers", "Pulse"]}
    out = compare_groups(issues, matcher, topics, families, cap=10)
    assert out["per_repo"]["big/sdk"]["n_issues"] == 100
    assert out["per_repo"]["big/sdk"]["patterns"]["transpilation_compilation"] == pytest.approx(0.5)
    assert out["per_repo"]["small/lib"]["topics"] == {"1": 1.0}
    assert out["per_family"]["Compilers"]["n_issues"] == 104  # a repo counts in each of its families
    assert out["per_family"]["Pulse"]["n_issues"] == 4
    assert out["per_family"]["Pulse"]["patterns"]["pulse_control"] == 1.0


def test_repos_without_a_family_are_grouped_as_uncategorized(matcher):
    out = compare_groups(_corpus(), matcher, {}, {}, cap=10)
    assert set(out["per_family"]) == {"uncategorized"}


def test_capped_sensitivity_run_limits_each_repo_and_reports_the_shift(matcher):
    out = compare_groups(_corpus(), matcher, {}, {}, cap=10)
    assert out["global"]["n_issues"] == 104
    assert out["capped"]["cap"] == 10 and out["capped"]["n_issues"] == 14
    # uncapped the big repo dominates; capped the small repo's pulse share rises
    assert out["capped"]["patterns"]["pulse_control"] > out["global"]["patterns"]["pulse_control"]
    again = compare_groups(_corpus(), matcher, {}, {}, cap=10)
    assert again["capped"] == out["capped"]  # deterministic


def test_load_repo_families_splits_catalog_categories(make_db):
    db = make_db(items=[{"repo": "a/b", "number": 1}])
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE repo_catalog (repo TEXT PRIMARY KEY, categories TEXT)")
    conn.execute("INSERT INTO repo_catalog VALUES ('a/b', 'Quantum compilers | Quantum full-stack libraries')")
    conn.execute("INSERT INTO repo_catalog VALUES ('c/d', NULL)")
    conn.commit()
    conn.close()
    assert load_repo_families(db) == {"a/b": ["Quantum compilers", "Quantum full-stack libraries"], "c/d": []}
    assert load_repo_families(db.parent / "missing.db") == {}


def test_metrics_run_writes_comparisons_next_to_the_metrics_json(config, tmp_path):
    import json
    from tests.test_metrics import _run_metrics

    config.input.db_path = tmp_path / "missing.db"
    _run_metrics(config, tmp_path, [_issue("a/a", 1, "transpile fails"), _issue("b/b", 1, "tea")])
    data = json.loads((tmp_path / "comparisons.json").read_text(encoding="utf-8"))
    assert set(data) == {"per_repo", "per_family", "global", "capped"}
    assert data["per_repo"]["a/a"]["patterns"]["transpilation_compilation"] == 1.0
