"""Tests for issue-template stripping (S12)."""

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
                  "Please search", "I have searched"):
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
