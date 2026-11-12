"""Tests for author-based bot filtering (S9)."""

import pytest

from src.models import RawIssue, is_bot_user
from src.preprocess import IssuePreprocessor


@pytest.fixture
def preprocessor(config):
    return IssuePreprocessor(config)


NAMES = ["qiskit-bot", "claassistant", "pre-commit-ci", "codecov-commenter", "stale", "bors"]


class TestIsBotUser:
    def test_exact_name_list_is_case_insensitive(self):
        assert is_bot_user("Qiskit-Bot", NAMES)
        assert is_bot_user("CLAassistant", NAMES)

    def test_bot_suffix(self):
        assert is_bot_user("dependabot[bot]", [])

    def test_author_type_bot(self):
        assert is_bot_user("someone", [], author_type="Bot")
        assert is_bot_user("someone", [], author_type="bot")

    def test_human_with_substring_is_not_bot(self):
        assert not is_bot_user("both", NAMES)
        assert not is_bot_user("abbotsford", NAMES)
        assert not is_bot_user("mystale", NAMES)

    def test_none_author_is_not_bot(self):
        assert not is_bot_user(None, NAMES)


class TestPreprocessorBots:
    def _comment(self, author, author_type=None):
        return {"author": author, "author_type": author_type,
                "created_at": "2024-01-02T00:00:00Z", "body": "A reasonably long comment body here."}

    def test_default_config_drops_named_bots(self, preprocessor):
        for name in ["qiskit-bot", "x[bot]"]:
            assert preprocessor.clean_comment(self._comment(name)) is None
        assert preprocessor.clean_comment(self._comment("anyone", "Bot")) is None

    def test_default_config_keeps_human_named_both(self, preprocessor):
        assert preprocessor.clean_comment(self._comment("both")) is not None

    def test_bot_authored_issue_is_dropped_and_counted(self, preprocessor, tmp_path):
        base = dict(repo="a/b", title="Real issue title", body="x" * 80, state="open",
                    created_at="2024-01-01T00:00:00Z")
        issues = [
            RawIssue(issue_number=1, author="human", **base),
            RawIssue(issue_number=2, author="qiskit-bot", **base),
            RawIssue(issue_number=3, author="renovate[bot]", **base),
            RawIssue(issue_number=4, author="x", author_type="Bot", **base),
        ]
        stats = preprocessor.process_items(issues, tmp_path / "out.jsonl")
        assert stats["kept"] == 1
        assert stats["bot_issues"] == 3
