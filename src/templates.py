"""Quita el texto de plantilla de issues que no fue modificado (S12).

Solo se quitan marcadores estructurales: comentarios HTML y encabezados de plantilla
conocidos que ocupan una línea completa. Las listas de verificación no se quitan aquí,
porque una línea única de checklist es contenido real; las checklists de plantilla y las
plantillas por repo las maneja el filtro de líneas repetidas basado en datos, no listas de nombres.
"""

import re

HTML_COMMENT = re.compile(r"<!--[\s\S]*?-->")
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
    return text
