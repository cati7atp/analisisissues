"""--output-dir redirige juntas las salidas de patterns y metrics (S19)."""

import json
from datetime import datetime
from pathlib import Path

import yaml
from typer.testing import CliRunner

from src.cli import app
from tests.test_metrics import _write_issues
from src.models import CleanedIssue

runner = CliRunner()
ROOT = Path(__file__).resolve().parent.parent


def _issue(repo, n, text):
    return CleanedIssue(repo=repo, issue_number=n, title=text, cleaned_body="", state="open",
                        created_at=datetime(2024, 1, 1), author="u", full_text=text)


def _setup(tmp_path):
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    defaults = tmp_path / "defaults"
    cfg["paths"] = {k: str(defaults / Path(v).name) for k, v in cfg["paths"].items()}
    cfg["input"]["db_path"] = str(tmp_path / "missing.db")
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    issues = [_issue("a/a", 1, "transpile fails"), _issue("b/b", 1, "pulse schedule broken")]
    issues_file = tmp_path / "issues.jsonl"
    _write_issues(issues_file, issues)
    out = tmp_path / "out"
    out.mkdir()
    (out / "topics.jsonl").write_text(json.dumps(
        {"topic_id": 0, "name": "0_x", "keywords": ["x"], "count": 2}) + "\n", encoding="utf-8")
    (out / "doc_topics.jsonl").write_text("\n".join(
        json.dumps({"issue_id": i.issue_id, "topic_id": 0, "probability": 1.0}) for i in issues) + "\n",
        encoding="utf-8")
    return cfg_path, issues_file, out, defaults


def test_patterns_and_metrics_outputs_follow_output_dir(tmp_path):
    cfg, issues_file, out, defaults = _setup(tmp_path)
    r = runner.invoke(app, ["extract-patterns", "--config", str(cfg), "--issues", str(issues_file),
                            "--output-dir", str(out)])
    assert r.exit_code == 0, r.output
    r = runner.invoke(app, ["compute-metrics", "--config", str(cfg), "--issues", str(issues_file),
                            "--output-dir", str(out)])
    assert r.exit_code == 0, r.output
    for name in ["quantum_patterns.jsonl", "pattern_summary.csv", "candidate_categories.jsonl",
                 "maintainability_metrics.json", "maintainability_summary.csv", "comparisons.json"]:
        assert (out / name).exists(), name
    assert not defaults.exists()  # nada se filtró a las rutas configuradas
    metrics = json.loads((out / "maintainability_metrics.json").read_text(encoding="utf-8"))
    assert metrics["per_repo"][0]["top_topics"] == [{"topic_id": 0, "count": 1, "percentage": 100.0}]
