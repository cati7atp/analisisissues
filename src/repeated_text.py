"""Corpus-level repeated-text detection (S12), data-driven and streaming.

A line that occurs in many distinct issues is template or bot boilerplate. Counts use
64-bit hashes of normalized lines so the index stays small for a 36k-issue corpus.
"""

import hashlib
import re
from collections import Counter
from typing import Iterable, Set

from .code_summary import BUILD_MARKER, CODE_MARKER

EXEMPT_PREFIXES = (CODE_MARKER, BUILD_MARKER)  # structured summaries carry signal
MIN_ALNUM_CHARS = 4
_URL = re.compile(r"https?://\S+")
_NUMBER = re.compile(r"\d+")
_SPACE = re.compile(r"\s+")


def normalize_line(line: str) -> str:
    """Lowercase, collapse whitespace, mask URLs and digits so version bumps collapse."""
    text = _URL.sub("url", line.lower())
    return _SPACE.sub(" ", _NUMBER.sub("0", text)).strip()


def is_countable(line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith(EXEMPT_PREFIXES):
        return False
    return sum(ch.isalnum() for ch in stripped) >= MIN_ALNUM_CHARS


def _key(text: str) -> int:
    return int.from_bytes(hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest(), "big")


class RepeatedTextIndex:
    """Counts distinct issues per normalized line, then filters lines at or above a threshold."""

    def __init__(self, min_line_issues: int, min_comment_issues: int = 0):
        self.min_line_issues = min_line_issues
        self.min_comment_issues = min_comment_issues
        self.line_counts: Counter = Counter()
        self.comment_counts: Counter = Counter()
        self.removed_line_occurrences = 0
        self.dropped_comments = 0

    def add_issue(self, lines: Iterable[str], comments: Iterable[str] = ()) -> None:
        keys: Set[int] = {_key(normalize_line(l)) for l in lines if is_countable(l)}
        self.line_counts.update(keys)
        self.comment_counts.update({_key(normalize_line(c)) for c in comments if is_countable(c)})

    def is_repeated_comment(self, text: str) -> bool:
        return (
            self.min_comment_issues > 0
            and is_countable(text)
            and self.comment_counts[_key(normalize_line(text))] >= self.min_comment_issues
        )

    @property
    def repeated_comments(self) -> int:
        if self.min_comment_issues <= 0:
            return 0
        return sum(1 for c in self.comment_counts.values() if c >= self.min_comment_issues)

    def is_repeated_line(self, line: str) -> bool:
        return (
            self.min_line_issues > 0
            and is_countable(line)
            and self.line_counts[_key(normalize_line(line))] >= self.min_line_issues
        )

    @property
    def repeated_lines(self) -> int:
        if self.min_line_issues <= 0:
            return 0
        return sum(1 for c in self.line_counts.values() if c >= self.min_line_issues)

    def filter_lines(self, text: str) -> str:
        kept = []
        for line in text.split("\n"):
            if self.is_repeated_line(line):
                self.removed_line_occurrences += 1
            else:
                kept.append(line)
        return "\n".join(kept)
