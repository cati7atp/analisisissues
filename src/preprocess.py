"""Data preprocessing and cleaning for GitHub issues."""

import json
import typer
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter

import pandas as pd
from tqdm import tqdm
import structlog

from .config import get_config, load_config
from .models import (
    RawIssue, CleanedIssue, CleanedComment,
    clean_text, classify_issue_type, is_bot_user, parse_datetime
)

logger = structlog.get_logger()


class IssuePreprocessor:
    """Preprocess and clean raw GitHub issues for analysis."""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.preprocessing_config = self.config.preprocessing
        self.bot_users = set(u.lower() for u in self.preprocessing_config.bot_users)
        self.system_labels = set(l.lower() for l in self.preprocessing_config.system_labels)
    
    def load_raw_issues(self, input_path: Path) -> List[RawIssue]:
        """Load raw issues from JSONL file."""
        issues = []
        logger.info("Loading raw issues", path=str(input_path))
        
        with open(input_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    issues.append(RawIssue(**data))
                except Exception as e:
                    logger.warning("Failed to parse line", line=line_num, error=str(e))
        
        logger.info("Loaded raw issues", count=len(issues))
        return issues
    
    def clean_comment(self, comment) -> Optional[CleanedComment]:
        """Clean a single comment. Accepts dict or RawComment."""
        if isinstance(comment, dict):
            author = comment.get("author", "").lower()
            body = comment.get("body", "") or ""
            created_at_str = comment.get("created_at", "")
        else:
            author = comment.author.lower()
            body = comment.body or ""
            created_at_str = comment.created_at if isinstance(comment.created_at, str) else str(comment.created_at)
        
        # Skip bot comments
        if is_bot_user(author, list(self.bot_users)):
            return None
        
        # Skip empty or very short comments
        if len(body.strip()) < self.preprocessing_config.min_body_length:
            return None
        
        # Skip system-like comments
        body_lower = body.lower()
        if any(label in body_lower for label in self.system_labels):
            return None
        
        # Clean the body
        cleaned_body = clean_text(
            body,
            strip_code_fences=self.preprocessing_config.strip_code_fences,
            normalize_whitespace=self.preprocessing_config.normalize_whitespace
        )
        
        # Truncate very long comments
        if len(cleaned_body) > self.preprocessing_config.max_comment_length:
            cleaned_body = cleaned_body[:self.preprocessing_config.max_comment_length] + "... [truncated]"
        
        try:
            created_at = parse_datetime(created_at_str)
        except Exception as e:
            logger.warning("Failed to parse comment datetime", author=author, error=str(e))
            created_at = datetime.utcnow()
        
        return CleanedComment(
            author=author,
            created_at=created_at,
            body=cleaned_body,
            original_body=body
        )
    
    def clean_issue(self, raw_issue: RawIssue) -> Optional[CleanedIssue]:
        """Clean a single issue with all its comments."""
        # Clean body
        raw_body = raw_issue.body or ""
        cleaned_body = clean_text(
            raw_body,
            strip_code_fences=self.preprocessing_config.strip_code_fences,
            normalize_whitespace=self.preprocessing_config.normalize_whitespace
        )
        
        # Skip issues with no meaningful content
        if len(cleaned_body) < self.preprocessing_config.min_body_length and not raw_issue.title.strip():
            logger.debug("Skipping issue with no content", repo=raw_issue.repo, number=raw_issue.issue_number)
            return None
        
        # Clean comments
        cleaned_comments = []
        seen_bodies = set()  # Deduplicate comments
        for comment in raw_issue.comments:
            cleaned = self.clean_comment(comment)
            if cleaned and cleaned.body not in seen_bodies:
                seen_bodies.add(cleaned.body)
                cleaned_comments.append(cleaned)
        
        # Classify issue type
        issue_type = classify_issue_type(raw_issue.title, raw_issue.body, raw_issue.labels)
        
        # Parse dates
        try:
            created_at = parse_datetime(raw_issue.created_at)
        except Exception:
            created_at = datetime.utcnow()
        
        closed_at = None
        if raw_issue.closed_at:
            try:
                closed_at = parse_datetime(raw_issue.closed_at)
            except Exception:
                pass
        
        # Build full text for topic modeling (title + body + comments)
        text_parts = [raw_issue.title]
        if cleaned_body:
            text_parts.append(cleaned_body)
        for comment in cleaned_comments:
            text_parts.append(comment.body)
        full_text = " ".join(text_parts)
        
        return CleanedIssue(
            repo=raw_issue.repo,
            issue_number=raw_issue.issue_number,
            title=raw_issue.title.strip(),
            body=raw_issue.body,
            cleaned_body=cleaned_body,
            state=raw_issue.state,
            labels=[l.lower() for l in raw_issue.labels],
            created_at=created_at,
            closed_at=closed_at,
            author=raw_issue.author.lower(),
            comments=cleaned_comments,
            assignees=[a.lower() for a in raw_issue.assignees],
            milestone=raw_issue.milestone,
            reactions=raw_issue.reactions,
            issue_type=issue_type,
            full_text=full_text
        )
    
    def process(self, input_path: Optional[Path] = None, output_path: Optional[Path] = None) -> List[CleanedIssue]:
        """Run the full preprocessing pipeline."""
        input_path = input_path or self.config.paths.raw_data
        output_path = output_path or self.config.paths.processed_data
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load and clean
        raw_issues = self.load_raw_issues(input_path)
        
        cleaned_issues = []
        stats = {"total": len(raw_issues), "kept": 0, "skipped": 0, "comments_removed": 0}
        
        for raw_issue in tqdm(raw_issues, desc="Preprocessing issues"):
            cleaned = self.clean_issue(raw_issue)
            if cleaned:
                cleaned_issues.append(cleaned)
                stats["kept"] += 1
            else:
                stats["skipped"] += 1
            
            # Count removed comments
            original_comment_count = len(raw_issue.comments)
            if cleaned:
                stats["comments_removed"] += original_comment_count - len(cleaned.comments)
            else:
                stats["comments_removed"] += original_comment_count
        
        # Save to JSONL
        logger.info("Saving cleaned issues", output=str(output_path), count=len(cleaned_issues))
        with open(output_path, "w", encoding="utf-8") as f:
            for issue in cleaned_issues:
                # Convert to dict with serializable dates
                data = issue.model_dump()
                data["created_at"] = issue.created_at.isoformat()
                if issue.closed_at:
                    data["closed_at"] = issue.closed_at.isoformat()
                for comment in data["comments"]:
                    comment["created_at"] = comment["created_at"].isoformat()
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        
        logger.info("Preprocessing complete", **stats)
        return cleaned_issues


def preprocess_cli(
    input_file: str = typer.Option(None, "--input", "-i", help="Input JSONL file"),
    output_file: str = typer.Option(None, "--output", "-o", help="Output JSONL file"),
    config_file: str = typer.Option("config.yaml", "--config", "-c", help="Config file path"),
):
    """Preprocess raw GitHub issues for analysis."""
    import typer
    from .config import load_config
    
    cfg = load_config(Path(config_file))
    preprocessor = IssuePreprocessor(cfg)
    
    input_path = Path(input_file) if input_file else cfg.paths.raw_data
    output_path = Path(output_file) if output_file else cfg.paths.processed_data
    
    issues = preprocessor.process(input_path, output_path)
    
    typer.echo(f"Processed {len(issues)} issues -> {output_path}")


if __name__ == "__main__":
    import typer
    typer.run(preprocess_cli)