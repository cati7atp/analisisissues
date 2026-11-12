"""Cabecera del informe generado: formato estable, sin depender del intérprete."""

import json
import re

from src.report import generate_report

GENERATED_HEADER = re.compile(r"^\*Generated: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00\*$")


def _metrics_file(tmp_path):
    payload = {
        "per_repo": [
            {"repo": "a/b", "total_issues": 2, "open_issues": 1, "closed_issues": 1,
             "issue_types": {"bug": 2}}
        ],
        "aggregated": {"total_repos": 1, "total_issues": 2},
    }
    path = tmp_path / "metrics.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_report_opens_with_generation_and_anonymization_header(config, tmp_path):
    output = tmp_path / "report.md"

    text = generate_report(
        config,
        _metrics_file(tmp_path),
        tmp_path / "topics.jsonl",
        tmp_path / "patterns.jsonl",
        output,
        anonymize=False,
    )

    lines = [line for line in text.splitlines() if line]
    assert lines[0] == "# Quantum Software Maintainability Analysis Report"
    assert GENERATED_HEADER.match(lines[1]), lines[1]
    assert lines[2] == "*Anonymized: False*"
    assert output.read_text(encoding="utf-8") == text
