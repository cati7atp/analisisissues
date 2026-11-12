"""Las personas se pseudonimizan antes de que algo salga del preprocesamiento."""

import pytest

from src.models import RawIssue, clean_text
from src.preprocess import IssuePreprocessor


def _raw(**over):
    data = {
        "repo": "qiskit/qiskit", "issue_number": 1, "title": "Crash reported by @bob-the-dev",
        "body": "Thanks @Alice, see @ian-HP-Stream-Laptop-11 and the optimizer fails to converge on hardware.",
        "state": "open", "labels": [], "created_at": "2024-01-15T10:30:00Z", "closed_at": None,
        "author": "RealPerson", "assignees": ["Alice", "carol"],
        "comments": [{"author": "Helper", "created_at": "2024-01-16T12:00:00Z",
                      "body": "Try increasing shots to 8192, @RealPerson."}],
    }
    data.update(over)
    return RawIssue(**data)


@pytest.fixture
def pre(config):
    return IssuePreprocessor(config)


def test_hyphenated_mentions_are_masked():
    assert "ian" not in clean_text("ping @ian-HP-Stream-Laptop-11 please")


def test_people_and_mentions_do_not_survive_in_the_cleaned_issue(pre):
    issue = pre.clean_issue(_raw())
    dumped = issue.model_dump_json().lower()
    for name in ("realperson", "alice", "carol", "helper", "bob-the-dev", "ian-hp"):
        assert name not in dumped, name
    assert issue.author.startswith("u_") and len(issue.author) == 14
    assert all(a.startswith("u_") for a in issue.assignees)
    assert issue.comments[0].author.startswith("u_")


def test_pseudonyms_are_stable_case_insensitive_and_distinguish_people(pre):
    a, b = pre.clean_issue(_raw()), pre.clean_issue(_raw(author="realperson", issue_number=2))
    assert a.author == b.author
    assert a.assignees[0] != a.assignees[1]
    assert pre.clean_issue(_raw()).comments[0].author != a.author


def test_salt_changes_pseudonyms(config):
    first = IssuePreprocessor(config).clean_issue(_raw()).author
    config.preprocessing.author_salt = "another-salt"
    assert IssuePreprocessor(config).clean_issue(_raw()).author != first


def test_anonymization_can_be_disabled(config):
    config.preprocessing.anonymize_authors = False
    issue = IssuePreprocessor(config).clean_issue(_raw())
    assert issue.author == "realperson" and issue.assignees == ["alice", "carol"]


def test_issue_with_null_body_is_cleaned(pre):
    issue = pre.clean_issue(_raw(body=None, title="Optimizer fails to converge on hardware backends"))
    assert issue is None or issue.body == ""


def test_emails_are_masked_with_their_local_part():
    text = clean_text("Contact ana.lopez@example.com or jane.doe+qa@mail.example.org about it")
    assert "ana.lopez" not in text and "jane.doe" not in text and "example.com" not in text
    assert text.count("[EMAIL]") == 2


def test_emails_do_not_survive_in_the_cleaned_issue(pre):
    raw = _raw(title="Ping ana.lopez@example.com", body="Reach me at b.mendez@example.org about optimizer convergence on hardware.",
               comments=[{"author": "h", "created_at": "2024-01-16T12:00:00Z", "body": "cc c.ferrer@example.net please"}])
    dumped = pre.clean_issue(raw).model_dump_json().lower()
    for leaked in ("ana.lopez", "jane.doe", "b.mendez", "c.ferrer", "example.com", "example.org", "example.net"):
        assert leaked not in dumped, leaked
