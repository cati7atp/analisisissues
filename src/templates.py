"""Strip untouched issue-template boilerplate (S12).

Only structural markers are removed: HTML comments, known template headings that
occupy a whole line, and unchecked checklist items. Repeated per-repo templates are
handled by the data-driven repeated-line filter, not by name lists.
"""

import re

HTML_COMMENT = re.compile(r"<!--[\s\S]*?-->")
UNCHECKED_BOX = re.compile(r"^\s*[-*+]\s*\[ \]\s.*$", re.MULTILINE)
TEMPLATE_HEADINGS = (
    "describe the bug", "environment", "steps to reproduce", "additional context",
    "expected behavior", "expected behaviour", "actual behavior", "actual behaviour",
    "to reproduce", "screenshots", "current behavior", "what is the expected behavior",
    "what is the current behavior", "what happened", "informations",
)
HEADING_LINE = re.compile(
    r"^\s*(?:#{1,6}\s*|\*\*|__)(?:" + "|".join(TEMPLATE_HEADINGS) + r")\??\s*:?\s*(?:\*\*|__)?\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def strip_templates(text: str) -> str:
    text = HTML_COMMENT.sub("", text)
    text = HEADING_LINE.sub("", text)
    return UNCHECKED_BOX.sub("", text)
