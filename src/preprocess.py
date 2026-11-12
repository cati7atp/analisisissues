"""Data preprocessing and cleaning for GitHub issues."""

import json
import re
import typer
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Set, Union
from datetime import datetime
from collections import Counter
import hashlib

import pandas as pd
from tqdm import tqdm
import structlog

from .config import get_config, load_config
from .repeated_text import RepeatedTextIndex, document_key
from .models import (
    RawIssue, CleanedIssue, CleanedComment,
    MENTION_PATTERN, clean_text, classify_issue_type, is_bot_user, parse_datetime, structure_text
)

logger = structlog.get_logger()

PLACEHOLDER_TOKENS = re.compile(r"\[(?:CODE_BLOCK|BUILD_LOG|CODE|URL)\]|@user|#issue")


def content_chars(title: str, cleaned_body: str) -> int:
    """Characters of real content in title plus body, ignoring placeholder markers (S13)."""
    return sum(len(PLACEHOLDER_TOKENS.sub("", t).strip()) for t in (title or "", cleaned_body or ""))


class IssuePreprocessor:
    """Preprocess and clean raw GitHub issues for analysis."""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.preprocessing_config = self.config.preprocessing
        self.bot_users = set(u.lower() for u in self.preprocessing_config.bot_users)
        self.last_skip_reason: Optional[str] = None
        self.datetime_failures = 0
        self.repeated_index: Optional[RepeatedTextIndex] = None
        self.automated_patterns = [
            re.compile(p, re.MULTILINE) for p in self.preprocessing_config.automated_comment_patterns
        ]
    
    def pseudonym(self, name: str) -> str:
        """Stable salted pseudonym for a person (case-insensitive); the name itself when disabled."""
        name = (name or "").lower()
        if not self.preprocessing_config.anonymize_authors or not name:
            return name
        digest = hashlib.sha256(f"{self.preprocessing_config.author_salt}:{name}".encode("utf-8")).hexdigest()
        return f"u_{digest[:12]}"

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
    
    def _line_filter(self) -> Optional[Callable[[str], str]]:
        return self.repeated_index.filter_lines if self.repeated_index else None

    def build_repeated_index(self, raw_issues: Iterable[RawIssue]) -> RepeatedTextIndex:
        """Pass 1: count distinct issues per normalized line (bodies and kept comments)."""
        cfg = self.preprocessing_config
        index = RepeatedTextIndex(cfg.repeated_line_min_issues, cfg.repeated_comment_min_issues)

        def structured(text: Optional[str]) -> str:
            return structure_text(text or "", cfg.strip_code_fences, cfg.strip_templates)

        for raw_issue in raw_issues:
            if is_bot_user(raw_issue.author, list(self.bot_users), raw_issue.author_type):
                continue
            lines = structured(raw_issue.body).split("\n")
            comments: List[str] = []
            for c in raw_issue.comments:
                if not self._is_dropped_comment(c):
                    comments.append(structured(c.get("body") if isinstance(c, dict) else c.body))
            for text in comments:
                lines += text.split("\n")
            index.add_issue(lines, comments)
        return index

    def _is_dropped_comment(self, comment) -> bool:
        """True when clean_comment would drop the comment before cleaning (bot, short, automated)."""
        if isinstance(comment, dict):
            author, author_type, body = (comment.get("author") or "").lower(), comment.get("author_type"), comment.get("body") or ""
        else:
            author, author_type, body = comment.author.lower(), comment.author_type, comment.body or ""
        return (
            is_bot_user(author, list(self.bot_users), author_type)
            or len(body.strip()) < self.preprocessing_config.min_body_length
            or any(p.search(body) for p in self.automated_patterns)
        )

    def clean_comment(self, comment) -> Optional[CleanedComment]:
        """Clean a single comment. Accepts dict or RawComment."""
        if isinstance(comment, dict):
            author = (comment.get("author") or "").lower()
            author_type = comment.get("author_type")
            body = comment.get("body", "") or ""
            created_at_str = comment.get("created_at", "")
        else:
            author = comment.author.lower()
            author_type = comment.author_type
            body = comment.body or ""
            created_at_str = comment.created_at if isinstance(comment.created_at, str) else str(comment.created_at)
        
        # Skip bot comments
        if is_bot_user(author, list(self.bot_users), author_type):
            return None
        
        # Skip empty or very short comments
        if len(body.strip()) < self.preprocessing_config.min_body_length:
            return None
        
        # Skip system-like comments
        if any(p.search(body) for p in self.automated_patterns):
            return None

        # Skip comments repeated across many issues (automated or templated, S12)
        if self.repeated_index and self.repeated_index.min_comment_issues > 0:
            structured = structure_text(
                body, self.preprocessing_config.strip_code_fences, self.preprocessing_config.strip_templates
            )
            if self.repeated_index.is_repeated_comment(structured):
                self.repeated_index.dropped_comments += 1
                return None

        # Clean the body
        cleaned_body = clean_text(
            body,
            strip_code_fences=self.preprocessing_config.strip_code_fences,
            strip_templates=self.preprocessing_config.strip_templates,
            line_filter=self._line_filter(),
            normalize_whitespace=self.preprocessing_config.normalize_whitespace
        )

        # Truncate very long comments
        if len(cleaned_body) > self.preprocessing_config.max_comment_length:
            cleaned_body = cleaned_body[:self.preprocessing_config.max_comment_length] + "... [truncated]"
        
        try:
            created_at = parse_datetime(created_at_str)
        except Exception as e:
            logger.warning("Failed to parse comment datetime", error=str(e))
            self.datetime_failures += 1
            return None
        
        return CleanedComment(
            author=self.pseudonym(author),
            created_at=created_at,
            body=cleaned_body,
        )
    
    def clean_issue(self, raw_issue: RawIssue) -> Optional[CleanedIssue]:
        """Clean a single issue with all its comments."""
        if is_bot_user(raw_issue.author, list(self.bot_users), raw_issue.author_type):
            logger.debug("Skipping bot-authored issue", repo=raw_issue.repo, number=raw_issue.issue_number)
            self.last_skip_reason = "bot_issue"
            return None
        self.last_skip_reason = None

        # Clean body
        raw_body = raw_issue.body or ""
        cleaned_body = clean_text(
            raw_body,
            strip_code_fences=self.preprocessing_config.strip_code_fences,
            strip_templates=self.preprocessing_config.strip_templates,
            line_filter=self._line_filter(),
            normalize_whitespace=self.preprocessing_config.normalize_whitespace
        )
        
        # Skip issues with no meaningful content
        if content_chars(raw_issue.title, cleaned_body) < self.preprocessing_config.min_chars:
            logger.debug("Skipping issue with no content", repo=raw_issue.repo, number=raw_issue.issue_number)
            self.last_skip_reason = "empty_content"
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
            self.datetime_failures += 1
            self.last_skip_reason = "bad_created_at"
            return None

        closed_at = None
        if raw_issue.closed_at:
            try:
                closed_at = parse_datetime(raw_issue.closed_at)
            except Exception:
                self.datetime_failures += 1
        
        # Build full text for topic modeling (title + body + comments)
        text_parts = [MENTION_PATTERN.sub("@user", raw_issue.title)]
        if cleaned_body:
            text_parts.append(cleaned_body)
        for comment in cleaned_comments:
            text_parts.append(comment.body)
        full_text = " ".join(text_parts)
        
        return CleanedIssue(
            repo=raw_issue.repo,
            issue_number=raw_issue.issue_number,
            title=MENTION_PATTERN.sub("@user", raw_issue.title.strip()),
            body=MENTION_PATTERN.sub("@user", raw_issue.body),
            cleaned_body=cleaned_body,
            state=raw_issue.state,
            labels=[l.lower() for l in raw_issue.labels],
            created_at=created_at,
            closed_at=closed_at,
            author=self.pseudonym(raw_issue.author),
            comments=cleaned_comments,
            assignees=[self.pseudonym(a) for a in raw_issue.assignees],
            milestone=raw_issue.milestone,
            reactions=raw_issue.reactions,
            state_reason=raw_issue.state_reason,
            item_type=raw_issue.item_type or "issue",
            issue_type=issue_type,
            full_text=full_text
        )
    
    def iter_raw_issues(self, input_path: Path) -> Iterator[RawIssue]:
        """Stream raw issues from a legacy JSONL file."""
        with open(input_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield RawIssue(**json.loads(line))
                except Exception as e:
                    logger.warning("Failed to parse line", line=line_num, error=str(e))

    @staticmethod
    def _serialize(issue: CleanedIssue) -> str:
        data = issue.model_dump()
        data["created_at"] = issue.created_at.isoformat()
        if issue.closed_at:
            data["closed_at"] = issue.closed_at.isoformat()
        for comment in data["comments"]:
            comment["created_at"] = comment["created_at"].isoformat()
        return json.dumps(data, ensure_ascii=False) + "\n"

    def process_items(
        self,
        raw_issues: Union[Iterable[RawIssue], Callable[[], Iterable[RawIssue]]],
        output_path: Optional[Path] = None,
        chunk_size: int = 500,
    ) -> Dict[str, int]:
        """Clean raw issues as a stream and write JSONL in chunks; return counts.

        Pass a callable returning a fresh iterable to enable the two-pass repeated-text
        filters (S12): pass 1 counts lines across issues, pass 2 cleans and writes.
        """
        output_path = output_path or self.config.paths.processed_data
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.repeated_index = None
        if callable(raw_issues):
            if self.preprocessing_config.repeated_line_min_issues > 0 or self.preprocessing_config.repeated_comment_min_issues > 0:
                self.repeated_index = self.build_repeated_index(raw_issues())
            raw_issues = raw_issues()
        stats = {"total": 0, "kept": 0, "skipped": 0, "comments_removed": 0, "bot_issues": 0,
                 "repeated_lines": 0, "repeated_line_removals": 0,
                 "repeated_comments": 0, "repeated_comment_drops": 0, "duplicates": 0,
                 "empty_content": 0, "datetime_failures": 0}
        self.datetime_failures = 0
        seen_documents: Set[int] = set()
        chunk: List[str] = []
        with open(output_path, "w", encoding="utf-8") as f:
            for raw_issue in tqdm(raw_issues, desc="Preprocessing issues"):
                stats["total"] += 1
                cleaned = self.clean_issue(raw_issue)
                original_comments = len(raw_issue.comments)
                if cleaned and self.preprocessing_config.drop_exact_duplicates:
                    key = document_key(cleaned.title, cleaned.cleaned_body)
                    if key in seen_documents:
                        stats["duplicates"] += 1
                        cleaned = None
                    else:
                        seen_documents.add(key)
                if cleaned:
                    stats["kept"] += 1
                    stats["comments_removed"] += original_comments - len(cleaned.comments)
                    chunk.append(self._serialize(cleaned))
                    if len(chunk) >= chunk_size:
                        f.writelines(chunk)
                        chunk.clear()
                else:
                    stats["skipped"] += 1
                    if self.last_skip_reason == "empty_content":
                        stats["empty_content"] += 1
                    if self.last_skip_reason == "bot_issue":
                        stats["bot_issues"] += 1
                    stats["comments_removed"] += original_comments
            f.writelines(chunk)
        stats["datetime_failures"] = self.datetime_failures
        if self.repeated_index:
            stats["repeated_lines"] = self.repeated_index.repeated_lines
            stats["repeated_line_removals"] = self.repeated_index.removed_line_occurrences
            stats["repeated_comments"] = self.repeated_index.repeated_comments
            stats["repeated_comment_drops"] = self.repeated_index.dropped_comments
        logger.info("Preprocessing complete", output=str(output_path), **stats)
        return stats

    def process(self, input_path: Optional[Path] = None, output_path: Optional[Path] = None) -> Dict[str, int]:
        """Legacy JSONL entry point: stream input_path through process_items."""
        input_path = input_path or self.config.paths.raw_data
        logger.info("Loading raw issues", path=str(input_path))
        return self.process_items(self.iter_raw_issues(input_path), output_path)


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
    
    stats = preprocessor.process(input_path, output_path)
    
    typer.echo(f"Processed {stats['kept']} issues -> {output_path}")


if __name__ == "__main__":
    import typer
    typer.run(preprocess_cli)