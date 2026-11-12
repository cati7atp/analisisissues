"""Pydantic models for quantum issues analysis."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from collections import Counter
import re

from .code_summary import summarize_fenced_code, summarize_tracebacks


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
    issue_type: IssueType = "other"
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


class RepoMetrics(BaseModel):
    repo: str
    total_issues: int
    open_issues: int
    closed_issues: int
    issue_types: Dict[str, int]
    median_resolution_days: Optional[float] = None
    resolution_by_type: Dict[str, Optional[float]] = Field(default_factory=dict)
    reopen_rate: float = 0.0
    label_churn_per_issue: float = 0.0
    gini_contributors: float = 0.0
    unique_contributors: int = 0
    quantum_keyword_ratios: Dict[str, float] = Field(default_factory=dict)
    topic_entropy: float = 0.0
    top_topics: List[Dict[str, Any]] = Field(default_factory=list)


class AggregatedMetrics(BaseModel):
    total_repos: int
    total_issues: int
    overall_median_resolution_days: Optional[float] = None
    overall_reopen_rate: float = 0.0
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
INLINE_CODE_PATTERN = re.compile(r"`[^`]+`")
URL_PATTERN = re.compile(r"https?://\S+")
MENTION_PATTERN = re.compile(r"@\w+")
ISSUE_REF_PATTERN = re.compile(r"#\d+")


def clean_text(text: str, strip_code_fences: bool = True, normalize_whitespace: bool = True) -> str:
    """Clean markdown text for analysis."""
    if not text:
        return ""
    
    result = text
    
    if strip_code_fences:
        result = summarize_fenced_code(result)
        result = summarize_tracebacks(result)
        result = INLINE_CODE_PATTERN.sub("[CODE]", result)
    
    result = URL_PATTERN.sub("[URL]", result)
    result = MENTION_PATTERN.sub("@user", result)
    result = ISSUE_REF_PATTERN.sub("#issue", result)
    
    if normalize_whitespace:
        result = re.sub(r"\s+", " ", result).strip()
    
    return result


def classify_issue_type(title: str, body: Optional[str], labels: List[str]) -> IssueType:
    """Classify issue type from title, body, and labels."""
    text = f"{title} {body or ''}".lower()
    label_text = " ".join(labels).lower()
    
    bug_keywords = ["bug", "error", "fail", "crash", "broken", "issue", "problem", "defect", "exception"]
    feature_keywords = ["feature", "enhancement", "request", "add", "implement", "support", "proposal"]
    question_keywords = ["question", "how to", "help", "ask", "doubt", "unclear", "confused"]
    
    if any(kw in label_text for kw in ["bug", "type:bug", "kind/bug"]):
        return "bug"
    if any(kw in label_text for kw in ["feature", "enhancement", "type:feature", "kind/feature"]):
        return "feature"
    if any(kw in label_text for kw in ["question", "help wanted", "type:question", "kind/question"]):
        return "question"
    if any(kw in label_text for kw in ["discussion", "type:discussion", "kind/discussion"]):
        return "discussion"
    
    # Heuristic from text
    if any(kw in text for kw in bug_keywords):
        return "bug"
    if any(kw in text for kw in feature_keywords):
        return "feature"
    if any(kw in text for kw in question_keywords):
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


def parse_datetime(dt_str: str) -> datetime:
    """Parse ISO8601 datetime string."""
    # Handle various GitHub datetime formats
    for fmt in [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    ]:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    # Fallback: try dateutil parser if available
    try:
        from dateutil import parser
        return parser.isoparse(dt_str)
    except Exception:
        raise ValueError(f"Unable to parse datetime: {dt_str}")