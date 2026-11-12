"""Los modelos de entrada son tolerantes; los rechazos se cuentan por motivo."""

from src.models import RawComment, RawIssue, RejectionCounter

BASE = {"repo": "a/b", "issue_number": 1, "title": "t", "created_at": "2024-01-01T00:00:00Z"}


def test_null_author_and_body_accepted():
    issue = RawIssue(**BASE, state="open", author=None, body=None)
    assert issue.author == ""
    assert issue.body is None


def test_state_any_casing_accepted():
    assert RawIssue(**BASE, state="CLOSED", author="x").state == "closed"
    assert RawIssue(**BASE, state=" Open ", author="x").state == "open"


def test_unknown_extra_columns_ignored():
    issue = RawIssue(**BASE, state="open", author="x", html_url="u", locked=0)
    assert issue.repo == "a/b"


def test_comment_null_author_and_body():
    c = RawComment(author=None, created_at="2024-01-01T00:00:00Z", body=None)
    assert c.author == "" and c.body == ""


def test_rejection_counter_counts_by_reason():
    rc = RejectionCounter()
    rc.add("bad_created_at", {"repo": "a/b", "number": 1})
    rc.add("bad_created_at", {"repo": "a/b", "number": 2})
    rc.add("bad_number", {"repo": "a/b"})
    assert rc.by_reason == {"bad_created_at": 2, "bad_number": 1}
    assert rc.total == 3
    assert len(rc.samples) == 3
