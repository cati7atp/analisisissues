"""Tipo de issue: primero el `type` del dataset; el clasificador por palabras clave va como campo secundario."""

from src.models import RawIssue, classify_issue_type
from src.preprocess import IssuePreprocessor


def _raw(**kw):
    base = dict(repo="a/b", issue_number=1, title="Circuit depth grows after transpile",
                body="The transpiled circuit is much deeper than expected.", state="open",
                author="u", created_at="2024-01-01T00:00:00Z")
    base.update(kw)
    return RawIssue(**base)


def test_item_type_comes_from_dataset_type(config):
    cleaned = IssuePreprocessor(config).clean_issue(_raw(item_type="issue"))
    assert cleaned.item_type == "issue"


def test_keywords_match_whole_words_only():
    # "address" contiene "add" y "debugging" contiene "bug"; ninguna es una señal
    assert classify_issue_type("Address book", "debugging notes", []) == "discussion"


def test_help_wanted_label_is_not_a_question():
    assert classify_issue_type("Hello world", "", ["help wanted"]) == "discussion"


def test_real_signals_still_classified():
    assert classify_issue_type("Crash on import", "", []) == "bug"
    assert classify_issue_type("Hello", "", ["kind/bug"]) == "bug"
    assert classify_issue_type("Hello", "", ["enhancement"]) == "feature"
    assert classify_issue_type("Hello", "", ["question"]) == "question"
    assert classify_issue_type("Please add dark mode", "", []) == "feature"
    assert classify_issue_type("How to run on hardware", "", []) == "question"
