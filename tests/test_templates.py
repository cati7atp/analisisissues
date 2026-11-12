"""Tests de la eliminación de plantillas de issues (S12)."""

from src.models import clean_text

TEMPLATE = """<!-- Please search existing issues before filing -->
### Describe the bug
The transpiler loses a barrier.

**Environment**
- [ ] I have searched the existing issues
- [x] I am using the latest version
## Steps to reproduce
1. run transpile

### Additional context:
"""


def test_template_headings_html_comments_and_unchecked_boxes_are_removed():
    result = clean_text(TEMPLATE)
    for noise in ("Describe the bug", "Environment", "Steps to reproduce", "Additional context",
                  "Please search"):
        assert noise not in result


def test_user_content_and_checked_boxes_are_kept():
    result = clean_text(TEMPLATE)
    assert "The transpiler loses a barrier." in result
    assert "run transpile" in result
    assert "I am using the latest version" in result


def test_multiline_html_comment_is_removed():
    assert clean_text("Before <!-- line one\nline two --> after") == "Before after"


def test_headings_inside_prose_are_kept():
    text = "The Environment variable QISKIT_HOME is ignored."
    assert clean_text(text) == text


def test_template_stripping_can_be_disabled():
    assert "Describe the bug" in clean_text("### Describe the bug\nx", strip_templates=False)


def test_unchecked_checklist_line_with_real_content_is_kept():
    text = "Plan:\n- [ ] Expose the Target gate map and property map.\n- [ ] fix `run()` in ConsolidateBlocks"
    result = clean_text(text)
    assert "Expose the Target gate map and property map." in result
    assert "ConsolidateBlocks" in result


def test_template_checklist_line_repeated_across_issues_is_still_removed(config, tmp_path):
    import json
    from src.models import RawIssue
    from src.preprocess import IssuePreprocessor

    template = "- [ ] If possible, make a PR with a failing test to give us a starting point"
    issues = [
        RawIssue(repo="a/b", issue_number=i, title="A reasonably long title", state="open", labels=[],
                 created_at="2024-01-01T00:00:00Z", author="human",
                 body=f"Problem {'w' + 'x' * i}z in the transpiler layout pass.\n{template}\n- [ ] Unique real task {'v' + 'x' * i}z")
        for i in range(25)
    ]
    out = tmp_path / "clean.jsonl"
    IssuePreprocessor(config).process_items(lambda: iter(issues), out)
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").split("\n") if l]
    assert all("failing test" not in r["cleaned_body"] for r in rows)
    assert all("Unique real task" in r["cleaned_body"] for r in rows)
