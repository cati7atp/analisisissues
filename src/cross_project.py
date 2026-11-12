"""Cross-project patterns: topics whose issues recur across several distinct repositories."""

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from .models import CleanedIssue, DocTopic, TopicInfo

CSV_COLUMNS = ["topic_id", "name", "cross_project", "n_repos", "n_supporting_repos", "n_issues",
               "top_repo", "top_repo_share", "evenness", "keywords", "supporting_repos"]


def _evenness(counts: List[int]) -> float:
    """Normalized Shannon entropy of the repo distribution: 1 = spread evenly, 0 = a single repo."""
    total = sum(counts)
    if len(counts) < 2 or total == 0:
        return 0.0
    entropy = -sum((c / total) * math.log(c / total) for c in counts if c)
    return entropy / math.log(len(counts))


def find_cross_project_topics(
    topics: List[TopicInfo],
    doc_topics: List[DocTopic],
    issues: List[CleanedIssue],
    min_repos: int,
    min_issues_per_repo: int,
    max_top_repo_share: float,
) -> List[Dict[str, Any]]:
    """One row per topic. A topic is cross-project when at least ``min_repos`` repos each hold
    ``min_issues_per_repo`` of its issues and no repo exceeds ``max_top_repo_share`` of it. The
    repo_specific flag (a different, stricter threshold) is informational here: one dominant repo
    does not stop a topic that recurs in many others from being a cross-project pattern.
    Outliers (topic -1) never count."""
    repo_of = {i.issue_id: i.repo for i in issues}
    repo_size = Counter(repo_of.values())
    per_topic: Dict[int, Counter] = defaultdict(Counter)
    examples: Dict[int, Dict[str, str]] = defaultdict(dict)
    for dt in doc_topics:
        repo = repo_of.get(dt.issue_id)
        if dt.topic_id == -1 or repo is None:
            continue
        per_topic[dt.topic_id][repo] += 1
        examples[dt.topic_id].setdefault(repo, dt.issue_id)

    rows = []
    for topic in topics:
        counts = per_topic.get(topic.topic_id)
        if not counts:
            continue
        n_issues = sum(counts.values())
        top_repo, top_n = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        supporting = sorted(r for r, n in counts.items() if n >= min_issues_per_repo)
        top_share = top_n / n_issues
        rows.append({
            "topic_id": topic.topic_id,
            "name": topic.name,
            "keywords": topic.keywords,
            "cross_project": len(supporting) >= min_repos and top_share <= max_top_repo_share,
            "repo_specific": topic.repo_specific,
            "n_repos": len(counts),
            "supporting_repos": supporting,
            "n_issues": n_issues,
            "top_repo": top_repo,
            "top_repo_share": top_share,
            "evenness": _evenness(list(counts.values())),
            "per_repo": {r: {"n": n, "prevalence": n / repo_size[r]} for r, n in sorted(counts.items())},
            "example_issue_ids": [examples[topic.topic_id][r] for r in sorted(counts)][:10],
        })
    rows.sort(key=lambda r: (not r["cross_project"], -len(r["supporting_repos"]), -r["n_issues"], r["topic_id"]))
    return rows


def write_cross_project_outputs(rows: List[Dict[str, Any]], jsonl_path: Path, csv_path: Path) -> None:
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    frame = pd.DataFrame([{
        **{k: r[k] for k in ("topic_id", "name", "cross_project", "n_repos", "n_issues",
                             "top_repo", "top_repo_share", "evenness")},
        "n_supporting_repos": len(r["supporting_repos"]),
        "keywords": ", ".join(r["keywords"][:8]),
        "supporting_repos": "|".join(r["supporting_repos"]),
    } for r in rows], columns=CSV_COLUMNS)
    frame.to_csv(csv_path, index=False, encoding="utf-8")
