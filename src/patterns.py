"""Quantum-specific pattern extraction from topics and issues."""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass

import pandas as pd
from tqdm import tqdm
import structlog

from .config import get_config
from .models import CleanedIssue, QuantumPattern, TopicInfo, DocTopic
from .taxonomy import TaxonomyMatcher, load_taxonomy

logger = structlog.get_logger()


@dataclass
class PatternMatch:
    pattern_id: str
    category: str
    issue_id: str
    matched_keywords: List[str]
    quote: str


def load_topics(topics_path: Path) -> List[TopicInfo]:
    """Load topics from JSONL."""
    topics = []
    with open(topics_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            topics.append(TopicInfo.model_validate_json(line))
    return topics


def load_doc_topics(doc_topics_path: Path) -> List[DocTopic]:
    """Load document-topic assignments from JSONL."""
    doc_topics = []
    with open(doc_topics_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            doc_topics.append(DocTopic.model_validate_json(line))
    return doc_topics


def load_issues(issues_path: Path) -> List[CleanedIssue]:
    """Load cleaned issues from JSONL."""
    issues = []
    with open(issues_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            from datetime import datetime
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            if data.get("closed_at"):
                data["closed_at"] = datetime.fromisoformat(data["closed_at"])
            for comment in data.get("comments", []):
                comment["created_at"] = datetime.fromisoformat(comment["created_at"])
            issues.append(CleanedIssue(**data))
    return issues


def build_keyword_patterns(config) -> TaxonomyMatcher:
    """Build the shared taxonomy matcher (the same one the metrics use)."""
    return TaxonomyMatcher(load_taxonomy(config.quantum_taxonomy))


def extract_quotes(text: str, keywords: List[str], max_quotes: int = 3, max_length: int = 200) -> List[str]:
    """Extract relevant quotes from text containing keywords."""
    quotes = []
    sentences = re.split(r"[.!?]+", text)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        # Check if sentence contains any keyword
        sentence_lower = sentence.lower()
        if any(kw.lower() in sentence_lower for kw in keywords):
            # Truncate if too long
            if len(sentence) > max_length:
                sentence = sentence[:max_length] + "..."
            quotes.append(sentence)
            if len(quotes) >= max_quotes:
                break
    
    return quotes


def find_pattern_matches(
    issues: List[CleanedIssue],
    matcher: TaxonomyMatcher,
    config,
) -> List[PatternMatch]:
    """Find all pattern matches across issues."""
    matches = []
    
    for issue in tqdm(issues, desc="Scanning for patterns"):
        full_text = issue.full_text
        if not full_text:
            continue
        
        for category, matched_keywords in matcher.match(full_text).items():
            quotes = extract_quotes(
                full_text,
                matched_keywords,
                max_quotes=config.report.max_example_quotes,
                max_length=config.report.quote_max_length,
            )
            matches.append(PatternMatch(
                pattern_id=f"{category}_{len(matches)}",
                category=category,
                issue_id=issue.issue_id,
                matched_keywords=matched_keywords,
                quote=quotes[0] if quotes else "",
            ))

    return matches


def aggregate_patterns(matches: List[PatternMatch], names: Optional[Dict[str, str]] = None) -> List[QuantumPattern]:
    """Aggregate individual matches into pattern summaries."""
    # Group by category
    by_category: Dict[str, List[PatternMatch]] = defaultdict(list)
    for match in matches:
        by_category[match.category].append(match)
    
    patterns = []
    for category, cat_matches in by_category.items():
        # Count unique issues per keyword
        keyword_issue_counts: Dict[str, Set[str]] = defaultdict(set)
        all_quotes = []
        all_keywords = []
        
        for match in cat_matches:
            for kw in match.matched_keywords:
                keyword_issue_counts[kw].add(match.issue_id)
            all_keywords.extend(match.matched_keywords)
            if match.quote:
                all_quotes.append(match.quote)
        
        # Create sub-patterns for each keyword that appears in multiple issues
        # Or create one pattern per category with all keywords
        # We'll create one pattern per category with top keywords
        
        # Get top keywords by frequency
        keyword_freq = {kw: len(issues) for kw, issues in keyword_issue_counts.items()}
        top_keywords = sorted(keyword_freq.keys(), key=lambda k: keyword_freq[k], reverse=True)[:10]
        
        # All unique issue IDs for this category
        all_issue_ids = set()
        for match in cat_matches:
            all_issue_ids.add(match.issue_id)
        
        pattern = QuantumPattern(
            pattern_id=category,
            name=(names or {}).get(category, category.replace("_", " ").title()),
            description=f"Issues related to {category.replace('_', ' ')} in quantum software development",
            category=category,
            supporting_issue_ids=sorted(all_issue_ids),
            frequency=len(all_issue_ids),
            example_quotes=all_quotes[:3],
            keywords_matched=top_keywords,
        )
        patterns.append(pattern)
    
    # Sort by frequency descending
    patterns.sort(key=lambda p: p.frequency, reverse=True)
    return patterns


def extract_quantum_patterns(
    config,
    topics_path: Path,
    issues_path: Path,
    output_path: Path,
) -> List[QuantumPattern]:
    """Extract quantum-specific patterns from topics and issues."""
    logger.info("Loading data for pattern extraction")
    
    # Load data
    topics = load_topics(topics_path)
    issues = load_issues(issues_path)
    
    # Build keyword patterns from config
    matcher = build_keyword_patterns(config)
    
    # Find matches
    logger.info("Finding pattern matches")
    matches = find_pattern_matches(issues, matcher, config)
    logger.info("Found matches", count=len(matches))
    
    # Aggregate into patterns
    logger.info("Aggregating patterns")
    patterns = aggregate_patterns(matches, matcher.names)
    logger.info("Extracted patterns", count=len(patterns))
    
    # Save patterns JSONL
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for pattern in patterns:
            f.write(pattern.model_dump_json() + "\n")
    
    # Save pattern summary CSV
    csv_path = config.paths.pattern_summary_csv
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([{
        "pattern_id": p.pattern_id,
        "name": p.name,
        "category": p.category,
        "frequency": p.frequency,
        "keywords": ", ".join(p.keywords_matched[:5]),
        "example_quote": p.example_quotes[0] if p.example_quotes else "",
    } for p in patterns])
    df.to_csv(csv_path, index=False)
    logger.info("Saved pattern summary CSV", path=str(csv_path))
    
    return patterns


def enhance_with_topic_analysis(
    patterns: List[QuantumPattern],
    topics: List[TopicInfo],
    doc_topics: List[DocTopic],
    issues: List[CleanedIssue],
) -> List[QuantumPattern]:
    """Enhance patterns with topic model insights."""
    # Map issue_id -> topic_id
    issue_to_topic = {dt.issue_id: dt.topic_id for dt in doc_topics}
    
    # Map topic_id -> topic info
    topic_map = {t.topic_id: t for t in topics}
    
    # For each pattern, find associated topics
    for pattern in patterns:
        topic_counts = Counter()
        for issue_id in pattern.supporting_issue_ids:
            topic_id = issue_to_topic.get(issue_id, -1)
            if topic_id != -1:
                topic_counts[topic_id] += 1
        
        # Add top topics to pattern description
        if topic_counts:
            top_topics = topic_counts.most_common(3)
            topic_names = [topic_map[tid].name for tid, _ in top_topics if tid in topic_map]
            if topic_names:
                pattern.description += f" Associated topics: {', '.join(topic_names)}."
    
    return patterns


if __name__ == "__main__":
    import typer
    from .config import load_config
    
    cfg = load_config(Path("config.yaml"))
    patterns = extract_quantum_patterns(cfg, cfg.paths.topics_output, cfg.paths.processed_data, cfg.paths.patterns_output)
    print(f"Extracted {len(patterns)} patterns")