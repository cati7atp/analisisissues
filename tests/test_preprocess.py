"""Tests for preprocessing module."""

import json
import tempfile
from pathlib import Path
from datetime import datetime

import pytest

from src.models import (
    RawIssue, CleanedIssue, clean_text, classify_issue_type,
    is_bot_user, parse_datetime,
)
from src.preprocess import IssuePreprocessor
from src.config import load_config


@pytest.fixture
def preprocessor(config):
    return IssuePreprocessor(config)


@pytest.fixture
def sample_raw_issue():
    return {
        "repo": "qiskit/qiskit",
        "issue_number": 1,
        "title": "VQE convergence fails on real hardware",
        "body": "When running VQE on IBM Quantum hardware, the optimizer fails to converge. The simulation works fine but hardware gives different results.",
        "state": "open",
        "labels": ["bug", "quantum"],
        "created_at": "2024-01-15T10:30:00Z",
        "closed_at": None,
        "author": "testuser",
        "comments": [
            {"author": "helper", "created_at": "2024-01-16T12:00:00Z", "body": "Try increasing shots to 8192."},
            {"author": "dependabot", "created_at": "2024-01-17T00:00:00Z", "body": "Bump numpy from 1.24 to 1.26"},
        ],
        "assignees": [],
        "milestone": None,
        "reactions": {"+1": 5},
    }


class TestCleanText:
    def test_strip_code_fences(self):
        text = "Here is code:\n```python\nprint('hello')\n```\nEnd."
        result = clean_text(text, strip_code_fences=True)
        assert "[CODE_BLOCK]" in result
        assert "print('hello')" not in result

    def test_normalize_whitespace(self):
        text = "Multiple   spaces   and\n\n\nnewlines"
        result = clean_text(text, normalize_whitespace=True)
        assert "  " not in result

    def test_empty_text(self):
        assert clean_text("") == ""
        assert clean_text(None) == ""

    def test_url_replacement(self):
        text = "Check https://example.com for details"
        result = clean_text(text)
        assert "[URL]" in result
        assert "https://example.com" not in result


class TestClassifyIssueType:
    def test_bug_from_labels(self):
        assert classify_issue_type("Title", "Body", ["bug"]) == "bug"
        assert classify_issue_type("Title", "Body", ["type:bug"]) == "bug"

    def test_feature_from_labels(self):
        assert classify_issue_type("Title", "Body", ["feature"]) == "feature"
        assert classify_issue_type("Title", "Body", ["enhancement"]) == "feature"

    def test_question_from_labels(self):
        assert classify_issue_type("Title", "Body", ["question"]) == "question"

    def test_bug_from_text(self):
        assert classify_issue_type("App crashes", "Error on startup", []) == "bug"

    def test_feature_from_text(self):
        assert classify_issue_type("Add new feature", "Implement support", []) == "feature"

    def test_question_from_text(self):
        assert classify_issue_type("How to use", "Question about setup", []) == "question"


class TestIsBotUser:
    def test_bot_detected(self):
        assert is_bot_user("dependabot", ["dependabot", "renovate"])
        assert is_bot_user("github-actions[bot]", ["github-actions"])

    def test_human_not_bot(self):
        assert not is_bot_user("testuser", ["dependabot", "renovate"])


class TestParseDatetime:
    def test_standard_format(self):
        dt = parse_datetime("2024-01-15T10:30:00Z")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15

    def test_with_microseconds(self):
        dt = parse_datetime("2024-01-15T10:30:00.123456Z")
        assert dt.year == 2024
        assert dt.microsecond == 123456

    def test_with_offset(self):
        dt = parse_datetime("2024-01-15T10:30:00+00:00")
        assert dt.year == 2024


class TestIssuePreprocessor:
    def test_clean_comment_removes_bot(self, preprocessor):
        comment = {"author": "dependabot", "created_at": "2024-01-17T00:00:00Z", "body": "Bump numpy"}
        result = preprocessor.clean_comment(comment)
        assert result is None

    def test_clean_comment_keeps_human(self, preprocessor):
        comment = {"author": "helper", "created_at": "2024-01-16T12:00:00Z", "body": "Try increasing shots to 8192."}
        result = preprocessor.clean_comment(comment)
        assert result is not None
        assert result.author == "helper"

    def test_clean_issue(self, preprocessor, sample_raw_issue):
        raw = RawIssue(**sample_raw_issue)
        cleaned = preprocessor.clean_issue(raw)
        assert cleaned is not None
        assert cleaned.repo == "qiskit/qiskit"
        assert cleaned.issue_number == 1
        assert cleaned.issue_type == "bug"
        assert len(cleaned.comments) == 1  # bot comment removed
        assert cleaned.comments[0].author == "helper"

    def test_clean_issue_removes_duplicates(self, preprocessor):
        issue = {
            "repo": "test/test",
            "issue_number": 2,
            "title": "Test",
            "body": "Body",
            "state": "open",
            "labels": [],
            "created_at": "2024-01-15T10:30:00Z",
            "closed_at": None,
            "author": "user",
            "comments": [
                {"author": "a", "created_at": "2024-01-16T00:00:00Z", "body": "Same comment"},
                {"author": "b", "created_at": "2024-01-17T00:00:00Z", "body": "Same comment"},
            ],
        }
        raw = RawIssue(**issue)
        cleaned = preprocessor.clean_issue(raw)
        assert len(cleaned.comments) == 1

    def test_process_end_to_end(self, preprocessor, sample_raw_issue, tmp_path):
        # Write input JSONL
        input_file = tmp_path / "input.jsonl"
        with open(input_file, "w") as f:
            f.write(json.dumps(sample_raw_issue) + "\n")
        
        output_file = tmp_path / "output.jsonl"
        issues = preprocessor.process(input_file, output_file)
        
        assert issues["kept"] == 1
        assert output_file.exists()
        
        # Verify output format
        with open(output_file) as f:
            line = f.readline()
            data = json.loads(line)
            assert data["repo"] == "qiskit/qiskit"
            assert "issue_type" in data
            assert "cleaned_body" in data
            assert "full_text" in data

    def test_process_items_streams_generator_without_original_body(self, preprocessor, sample_raw_issue, tmp_path):
        def gen():
            for n in range(3):
                yield RawIssue(**{**sample_raw_issue, "issue_number": n + 1, "title": f"VQE convergence fails {n}"})

        out = tmp_path / "nested" / "clean.jsonl"
        stats = preprocessor.process_items(gen(), out)
        assert (stats["total"], stats["kept"]) == (3, 3)
        rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
        assert [r["issue_number"] for r in rows] == [1, 2, 3]
        assert all(rows[0]["comments"]) and "original_body" not in rows[0]["comments"][0]
