"""Cross-repo comparison views that control for repo imbalance (S24)."""

import random
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping

from .models import CleanedIssue
from .taxonomy import TaxonomyMatcher

UNCATEGORIZED = "uncategorized"


def load_repo_families(db_path: Path) -> Dict[str, List[str]]:
    """repo -> SDK families from ``repo_catalog.categories`` (pipe separated); {} if unavailable."""
    if not Path(db_path).exists():
        return {}
    conn = sqlite3.connect(f"{Path(db_path).resolve().as_uri()}?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT repo, categories FROM repo_catalog").fetchall()
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()
    return {repo: [c.strip() for c in (cats or "").split("|") if c.strip()] for repo, cats in rows}


def _shares(issues: List[CleanedIssue], pattern_hits: Mapping[str, List[str]],
            topics: Mapping[str, int]) -> Dict[str, Any]:
    n = len(issues)
    patterns: Counter = Counter()
    topic_counts: Counter = Counter()
    for issue in issues:
        patterns.update(pattern_hits.get(issue.issue_id, []))
        if issue.issue_id in topics:
            topic_counts[str(topics[issue.issue_id])] += 1
    return {
        "n_issues": n,
        "patterns": {c: v / n for c, v in sorted(patterns.items())},
        "topics": {t: v / n for t, v in sorted(topic_counts.items())},
    }


def _view(groups: Mapping[str, List[CleanedIssue]], hits, topics) -> Dict[str, Dict[str, Any]]:
    return {name: _shares(members, hits, topics) for name, members in sorted(groups.items())}


def compare_groups(
    issues: List[CleanedIssue],
    matcher: TaxonomyMatcher,
    topics: Mapping[str, int],
    families: Mapping[str, List[str]],
    cap: int,
    seed: int = 0,
) -> Dict[str, Any]:
    """Pattern and topic prevalence per repo, per SDK family, global and with at most ``cap`` issues per repo."""
    hits = {i.issue_id: list(matcher.match(i.full_text)) for i in issues}
    by_repo: Dict[str, List[CleanedIssue]] = defaultdict(list)
    for issue in issues:
        by_repo[issue.repo].append(issue)
    by_family: Dict[str, List[CleanedIssue]] = defaultdict(list)
    for repo, members in by_repo.items():
        for family in families.get(repo) or [UNCATEGORIZED]:
            by_family[family].extend(members)

    rng = random.Random(seed)
    capped: List[CleanedIssue] = []
    for repo in sorted(by_repo):
        members = sorted(by_repo[repo], key=lambda i: i.issue_number)
        capped.extend(members if len(members) <= cap else sorted(
            rng.sample(members, cap), key=lambda i: i.issue_number))

    return {
        "per_repo": _view(by_repo, hits, topics),
        "per_family": _view(by_family, hits, topics),
        "global": _shares(issues, hits, topics),
        "capped": {"cap": cap, **_shares(capped, hits, topics)},
    }
