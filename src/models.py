"""Pydantic models for quantum issues analysis."""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from collections import Counter
import re

from .code_summary import summarize_build_logs, summarize_fenced_code, summarize_tracebacks
from .templates import strip_templates as remove_templates


IssueType = Literal["bug", "feature", "question", "discussion", "other"]


def _none_to_empty(value: Any) -> Any:
    return "" if value is None else value


class RawComment(BaseModel):
    author: str = ""
    created_at: str  # ISO8601 string
    body: str = ""
    kind: Optional[str] = None
    author_type: Optional[str] = None

    _null_text = field_validator("author", "body", mode="before")(_none_to_empty)


class RawIssue(BaseModel):
    repo: str  # "owner/repo"
    issue_number: int
    title: str
    body: Optional[str] = None
    state: Literal["open", "closed"]
    labels: List[str] = Field(default_factory=list)
    created_at: str  # ISO8601
    closed_at: Optional[str] = None
    author: str = ""
    comments: List[RawComment] = Field(default_factory=list)
    assignees: List[str] = Field(default_factory=list)
    milestone: Optional[str] = None
    reactions: Dict[str, int] = Field(default_factory=dict)
    item_type: str = "issue"
    state_reason: Optional[str] = None
    author_type: Optional[str] = None
    merged_at: Optional[str] = None
    comment_count: Optional[int] = None
    complete: Optional[int] = None
    draft: Optional[int] = None
    category: Optional[str] = None

    _null_author = field_validator("author", mode="before")(_none_to_empty)

    @field_validator("state", mode="before")
    @classmethod
    def _normalize_state(cls, value: Any) -> Any:
        return value.strip().lower() if isinstance(value, str) else value


class RejectionCounter:
    """Counts rejected input rows by reason and keeps a bounded sample."""

    def __init__(self, max_samples: int = 1000) -> None:
        self.by_reason: Counter = Counter()
        self.samples: List[Dict[str, Any]] = []
        self._max_samples = max_samples

    @property
    def total(self) -> int:
        return sum(self.by_reason.values())

    def add(self, reason: str, row: Dict[str, Any]) -> None:
        self.by_reason[reason] += 1
        if len(self.samples) < self._max_samples:
            self.samples.append({"reason": reason, "row": row})


class CleanedComment(BaseModel):
    author: str
    created_at: datetime
    body: str


class CleanedIssue(BaseModel):
    repo: str
    issue_number: int
    title: str
    body: Optional[str] = None
    cleaned_body: str
    state: Literal["open", "closed"]
    labels: List[str] = Field(default_factory=list)
    created_at: datetime
    closed_at: Optional[datetime] = None
    author: str
    comments: List[CleanedComment] = Field(default_factory=list)
    assignees: List[str] = Field(default_factory=list)
    milestone: Optional[str] = None
    reactions: Dict[str, int] = Field(default_factory=dict)
    state_reason: Optional[str] = None
    item_type: str = "issue"  # dataset `type` column (authoritative)
    issue_type: IssueType = "other"  # secondary keyword classification
    full_text: str = ""  # Combined text for topic modeling

    @property
    def issue_id(self) -> str:
        return f"{self.repo}#{self.issue_number}"


class TopicInfo(BaseModel):
    topic_id: int
    name: str
    keywords: List[str]
    count: int
    representative_docs: List[str] = Field(default_factory=list)
    probability: Optional[float] = None


class DocTopic(BaseModel):
    issue_id: str
    topic_id: int
    probability: float


class QuantumPattern(BaseModel):
    pattern_id: str
    name: str
    description: str
    category: str
    supporting_issue_ids: List[str]
    frequency: int
    example_quotes: List[str] = Field(default_factory=list)
    keywords_matched: List[str] = Field(default_factory=list)
    topic_share: Optional[float] = None  # share of supporting issues that fall in a discovered topic


class RepoMetrics(BaseModel):
    repo: str
    total_issues: int
    open_issues: int
    closed_issues: int
    issue_types: Dict[str, int]
    median_resolution_days: Optional[float] = None
    resolution_by_type: Dict[str, Optional[float]] = Field(default_factory=dict)
    resolution_outcomes: Dict[str, int] = Field(default_factory=dict)  # closed issues by state_reason
    gini_contributors: float = 0.0
    unique_contributors: int = 0
    quantum_keyword_ratios: Dict[str, float] = Field(default_factory=dict)
    topic_entropy: float = 0.0
    top_topics: List[Dict[str, Any]] = Field(default_factory=list)


class AggregatedMetrics(BaseModel):
    total_repos: int
    total_issues: int
    overall_median_resolution_days: Optional[float] = None
    resolution_outcomes: Dict[str, int] = Field(default_factory=dict)
    overall_gini_contributors: float = 0.0
    avg_issues_per_repo: float = 0.0
    quantum_pattern_prevalence: Dict[str, float] = Field(default_factory=dict)
    category_distribution: Dict[str, int] = Field(default_factory=dict)


class MaintainabilityMetrics(BaseModel):
    per_repo: List[RepoMetrics]
    aggregated: AggregatedMetrics
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# Regex patterns for cleaning
CODE_FENCE_PATTERN = re.compile(r"```[\s\S]*?```", re.MULTILINE)
INLINE_CODE_PATTERN = re.compile(r"`[^`\n]+`")  # single line: a stray backtick must not pair across lines
URL_PATTERN = re.compile(r"https?://\S+")
MENTION_PATTERN = re.compile(r"@\w+")
ISSUE_REF_PATTERN = re.compile(r"#\d+")


def structure_text(text: str, strip_code_fences: bool = True, strip_templates: bool = True) -> str:
    """Line-preserving cleaning steps (code summaries, build logs, templates)."""
    result = text or ""
    if strip_code_fences:
        result = summarize_fenced_code(result)
        result = summarize_tracebacks(result)
        result = summarize_build_logs(result)
        result = INLINE_CODE_PATTERN.sub("[CODE]", result)
    if strip_templates:
        result = remove_templates(result)
    return result


def clean_text(
    text: str,
    strip_code_fences: bool = True,
    normalize_whitespace: bool = True,
    strip_templates: bool = True,
    line_filter: Optional[Callable[[str], str]] = None,
) -> str:
    """Clean markdown text for analysis.

    `line_filter` runs after the structural steps and before placeholders and
    whitespace collapsing, while line boundaries still exist.
    """
    if not text:
        return ""

    result = structure_text(text, strip_code_fences, strip_templates)
    if line_filter:
        result = line_filter(result)

    result = URL_PATTERN.sub("[URL]", result)
    result = MENTION_PATTERN.sub("@user", result)
    result = ISSUE_REF_PATTERN.sub("#issue", result)
    
    if normalize_whitespace:
        result = re.sub(r"\s+", " ", result).strip()
    
    return result


def _has_word(keywords: List[str], text: str) -> bool:
    """True when any keyword occurs in ``text`` as a whole word or phrase."""
    return any(re.search(r"\b" + re.escape(kw) + r"\b", text) for kw in keywords)


def classify_issue_type(title: str, body: Optional[str], labels: List[str]) -> IssueType:
    """Secondary keyword classification from labels, then title and body (whole words only)."""
    text = f"{title} {body or ''}".lower()
    label_text = " ".join(labels).lower()

    bug_keywords = ["bug", "error", "fail", "crash", "broken", "issue", "problem", "defect", "exception"]
    feature_keywords = ["feature", "enhancement", "request", "add", "implement", "support", "proposal"]
    question_keywords = ["question", "how to", "help", "ask", "doubt", "unclear", "confused"]

    if _has_word(["bug"], label_text):
        return "bug"
    if _has_word(["feature", "enhancement"], label_text):
        return "feature"
    if _has_word(["question"], label_text):
        return "question"
    if _has_word(["discussion"], label_text):
        return "discussion"

    if _has_word(bug_keywords, text):
        return "bug"
    if _has_word(feature_keywords, text):
        return "feature"
    if _has_word(question_keywords, text):
        return "question"

    return "discussion"


def is_bot_user(username: Optional[str], bot_users: List[str], author_type: Optional[str] = None) -> bool:
    """Check if an author is a bot: type Bot, a `[bot]` suffix or an exact listed name."""
    if author_type and author_type.strip().lower() == "bot":
        return True
    if not username:
        return False
    name = username.strip().lower()
    return name.endswith("[bot]") or name in {b.lower() for b in bot_users}


def to_utc(dt: datetime) -> datetime:
    """Return ``dt`` as timezone-aware UTC (naive values are taken as UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_datetime(dt_str: str) -> datetime:
    """Parse an ISO8601 datetime string into a timezone-aware UTC datetime."""
    for fmt in [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S",
    ]:
        try:
            return to_utc(datetime.strptime(dt_str, fmt))
        except ValueError:
            continue
    try:
        from dateutil import parser
        return to_utc(parser.isoparse(dt_str))
    except Exception:
        raise ValueError(f"Unable to parse datetime: {dt_str}")
