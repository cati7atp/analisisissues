"""Maintainability metrics computation for quantum GitHub issues."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter, defaultdict
import math

import pandas as pd
import numpy as np
from tqdm import tqdm
import structlog

from .config import get_config
from .models import (
    CleanedIssue, RepoMetrics, AggregatedMetrics, 
    MaintainabilityMetrics, QuantumPattern
)

logger = structlog.get_logger()


def load_issues(issues_path: Path) -> List[CleanedIssue]:
    """Load cleaned issues from JSONL."""
    issues = []
    with open(issues_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            if data.get("closed_at"):
                data["closed_at"] = datetime.fromisoformat(data["closed_at"])
            for comment in data.get("comments", []):
                comment["created_at"] = datetime.fromisoformat(comment["created_at"])
            issues.append(CleanedIssue(**data))
    return issues


def load_patterns(patterns_path: Path) -> List[QuantumPattern]:
    """Load patterns from JSONL."""
    patterns = []
    if not patterns_path.exists():
        return patterns
    with open(patterns_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            patterns.append(QuantumPattern.model_validate_json(line))
    return patterns


def compute_gini(values: List[float]) -> float:
    """Compute Gini coefficient."""
    if not values or len(values) == 1:
        return 0.0
    sorted_values = sorted(values)
    n = len(sorted_values)
    cumsum = np.cumsum(sorted_values)
    return (n + 1 - 2 * np.sum(cumsum) / cumsum[-1]) / n


def compute_resolution_time(issue: CleanedIssue) -> Optional[float]:
    """Compute resolution time in days."""
    if issue.closed_at and issue.created_at:
        delta = issue.closed_at - issue.created_at
        return delta.total_seconds() / 86400.0
    return None


def compute_reopen_rate(issues: List[CleanedIssue]) -> float:
    """Estimate reopen rate from state transitions (simplified)."""
    # Without event data, we approximate: issues that were closed but have recent comments
    # or issues with state "open" that have "closed" label or similar
    closed_issues = [i for i in issues if i.state == "closed"]
    if not closed_issues:
        return 0.0
    
    # Heuristic: issues with comments after close date might be reopened
    # Since we don't have event timeline, we use a proxy
    reopened = 0
    for issue in closed_issues:
        if issue.closed_at:
            # Check if any comment is after close date
            for comment in issue.comments:
                if comment.created_at > issue.closed_at:
                    reopened += 1
                    break
    
    return reopened / len(closed_issues) if closed_issues else 0.0


def compute_label_churn(issues: List[CleanedIssue]) -> float:
    """Compute average label changes per issue (proxy without event data)."""
    # Without event data, we can't compute true label churn
    # Return 0 as placeholder
    return 0.0


def compute_contributor_gini(issues: List[CleanedIssue]) -> float:
    """Compute Gini coefficient of issue authorship."""
    author_counts = Counter(issue.author for issue in issues)
    counts = list(author_counts.values())
    return compute_gini(counts)


def compute_topic_entropy(issues: List[CleanedIssue], doc_topics_path: Path) -> float:
    """Compute entropy of topic distribution."""
    # Load doc topics
    topic_counts = Counter()
    if doc_topics_path.exists():
        with open(doc_topics_path, "r") as f:
            for line in f:
                data = json.loads(line)
                if data["topic_id"] != -1:
                    topic_counts[data["topic_id"]] += 1
    
    if not topic_counts:
        return 0.0
    
    total = sum(topic_counts.values())
    probs = [c / total for c in topic_counts.values()]
    entropy = -sum(p * math.log2(p) for p in probs if p > 0)
    return entropy


def compute_quantum_keyword_ratios(issues: List[CleanedIssue], config, matcher=None) -> Dict[str, float]:
    """Share of issues matching each taxonomy category, using the matcher the patterns module uses."""
    from .patterns import build_keyword_patterns

    matcher = matcher or build_keyword_patterns(config)
    counts = {category: 0 for category in matcher.names}
    for issue in issues:
        for category in matcher.match(issue.full_text):
            counts[category] += 1
    total = len(issues)
    return {category: (count / total if total else 0.0) for category, count in counts.items()}


def get_top_topics_for_repo(issues: List[CleanedIssue], doc_topics_path: Path, top_n: int = 5) -> List[Dict[str, Any]]:
    """Get top topics for a repository."""
    # Map issue_id -> topic_id
    issue_to_topic = {}
    if doc_topics_path.exists():
        with open(doc_topics_path, "r") as f:
            for line in f:
                data = json.loads(line)
                if data["topic_id"] != -1:
                    issue_to_topic[data["issue_id"]] = data["topic_id"]
    
    # Count topics for this repo's issues
    repo_issue_ids = {issue.issue_id for issue in issues}
    topic_counts = Counter()
    for issue_id in repo_issue_ids:
        topic_id = issue_to_topic.get(issue_id)
        if topic_id and topic_id != -1:
            topic_counts[topic_id] += 1
    
    total = sum(topic_counts.values())
    if total == 0:
        return []
    
    return [
        {"topic_id": tid, "count": count, "percentage": round(count / total * 100, 1)}
        for tid, count in topic_counts.most_common(top_n)
    ]


def compute_repo_metrics(
    repo: str,
    issues: List[CleanedIssue],
    patterns: List[QuantumPattern],
    doc_topics_path: Path,
    config,
) -> RepoMetrics:
    """Compute metrics for a single repository."""
    if not issues:
        return RepoMetrics(repo=repo, total_issues=0, open_issues=0, closed_issues=0, issue_types={})
    
    # Basic counts
    total = len(issues)
    open_count = sum(1 for i in issues if i.state == "open")
    closed_count = total - open_count
    
    # Issue type distribution
    type_counts = Counter(i.issue_type for i in issues)
    
    # Resolution time
    resolution_times = [compute_resolution_time(i) for i in issues if i.state == "closed"]
    resolution_times = [t for t in resolution_times if t is not None]
    median_resolution = np.median(resolution_times) if resolution_times else None
    
    # Resolution by type
    resolution_by_type = {}
    for issue_type in ["bug", "feature", "question", "discussion", "other"]:
        type_times = [
            compute_resolution_time(i) for i in issues 
            if i.state == "closed" and i.issue_type == issue_type
        ]
        type_times = [t for t in type_times if t is not None]
        resolution_by_type[issue_type] = np.median(type_times) if type_times else None
    
    # Reopen rate
    reopen_rate = compute_reopen_rate(issues)
    
    # Label churn
    label_churn = compute_label_churn(issues)
    
    # Contributor Gini
    gini = compute_contributor_gini(issues)
    unique_contributors = len(set(i.author for i in issues))
    
    # Quantum keyword ratios
    quantum_ratios = compute_quantum_keyword_ratios(issues, config)
    
    # Topic entropy
    topic_entropy = compute_topic_entropy(issues, doc_topics_path)
    
    # Top topics
    top_topics = get_top_topics_for_repo(issues, doc_topics_path)
    
    return RepoMetrics(
        repo=repo,
        total_issues=total,
        open_issues=open_count,
        closed_issues=closed_count,
        issue_types=dict(type_counts),
        median_resolution_days=median_resolution,
        resolution_by_type=resolution_by_type,
        reopen_rate=reopen_rate,
        label_churn_per_issue=label_churn,
        gini_contributors=gini,
        unique_contributors=unique_contributors,
        quantum_keyword_ratios=quantum_ratios,
        topic_entropy=topic_entropy,
        top_topics=top_topics,
    )


def compute_aggregated_metrics(
    repo_metrics: List[RepoMetrics],
    patterns: List[QuantumPattern],
    all_issues: List[CleanedIssue],
) -> AggregatedMetrics:
    """Compute aggregated metrics across all repositories."""
    if not repo_metrics:
        return AggregatedMetrics(total_repos=0, total_issues=0)
    
    total_repos = len(repo_metrics)
    total_issues = sum(m.total_issues for m in repo_metrics)
    
    # Overall resolution time
    all_resolution_times = []
    for m in repo_metrics:
        if m.median_resolution_days:
            all_resolution_times.append(m.median_resolution_days)
    overall_median = np.median(all_resolution_times) if all_resolution_times else None
    
    # Overall reopen rate (weighted)
    total_closed = sum(m.closed_issues for m in repo_metrics)
    weighted_reopen = sum(m.reopen_rate * m.closed_issues for m in repo_metrics)
    overall_reopen = weighted_reopen / total_closed if total_closed > 0 else 0.0
    
    # Overall Gini
    all_authors = []
    for m in repo_metrics:
        # We don't have per-repo author lists, so approximate
        pass
    overall_gini = np.mean([m.gini_contributors for m in repo_metrics]) if repo_metrics else 0.0
    
    # Average issues per repo
    avg_issues = total_issues / total_repos if total_repos > 0 else 0.0
    
    # Quantum pattern prevalence
    pattern_prevalence = {p.pattern_id: p.frequency / total_issues for p in patterns}
    
    # Category distribution (issue types)
    category_dist = Counter()
    for m in repo_metrics:
        for cat, count in m.issue_types.items():
            category_dist[cat] += count
    
    return AggregatedMetrics(
        total_repos=total_repos,
        total_issues=total_issues,
        overall_median_resolution_days=overall_median,
        overall_reopen_rate=overall_reopen,
        overall_gini_contributors=overall_gini,
        avg_issues_per_repo=avg_issues,
        quantum_pattern_prevalence=pattern_prevalence,
        category_distribution=dict(category_dist),
    )


def compute_maintainability_metrics(
    config,
    issues_path: Path,
    patterns_path: Path,
    output_json: Path,
    output_csv: Path,
) -> MaintainabilityMetrics:
    """Compute maintainability metrics from issues and patterns."""
    logger.info("Loading data for metrics computation")
    
    issues = load_issues(issues_path)
    patterns = load_patterns(patterns_path)
    
    # Group issues by repo
    issues_by_repo: Dict[str, List[CleanedIssue]] = defaultdict(list)
    for issue in issues:
        issues_by_repo[issue.repo].append(issue)
    
    # Compute per-repo metrics
    logger.info("Computing per-repo metrics", n_repos=len(issues_by_repo))
    repo_metrics = []
    for repo, repo_issues in tqdm(issues_by_repo.items(), desc="Computing repo metrics"):
        metrics = compute_repo_metrics(
            repo, repo_issues, patterns, config.paths.doc_topics_output, config
        )
        repo_metrics.append(metrics)
    
    # Compute aggregated metrics
    aggregated = compute_aggregated_metrics(repo_metrics, patterns, issues)
    
    # Create full metrics object
    metrics = MaintainabilityMetrics(
        per_repo=repo_metrics,
        aggregated=aggregated,
    )
    
    # Save JSON
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        f.write(metrics.model_dump_json(indent=2))
    logger.info("Saved metrics JSON", path=str(output_json))
    
    # Save CSV summary
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([{
        "repo": m.repo,
        "total_issues": m.total_issues,
        "open_issues": m.open_issues,
        "closed_issues": m.closed_issues,
        "median_resolution_days": m.median_resolution_days,
        "reopen_rate": m.reopen_rate,
        "gini_contributors": m.gini_contributors,
        "unique_contributors": m.unique_contributors,
        "topic_entropy": m.topic_entropy,
        **{f"quantum_{k}": v for k, v in m.quantum_keyword_ratios.items()},
    } for m in repo_metrics])
    df.to_csv(output_csv, index=False)
    logger.info("Saved metrics CSV", path=str(output_csv))
    
    return metrics


if __name__ == "__main__":
    import typer
    from .config import load_config
    
    cfg = load_config(Path("config.yaml"))
    metrics = compute_maintainability_metrics(
        cfg, cfg.paths.processed_data, cfg.paths.patterns_output,
        cfg.paths.metrics_output, cfg.paths.metrics_csv
    )
    print(f"Computed metrics for {metrics.aggregated.total_repos} repos, {metrics.aggregated.total_issues} issues")