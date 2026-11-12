"""El CLI `preprocess` lee del dataset SQLite."""

import json

import yaml
from typer.testing import CliRunner

from src.cli import app

runner = CliRunner()


def _config(tmp_path, db, **input_overrides):
    cfg = yaml.safe_load((__import__("pathlib").Path(__file__).resolve().parent.parent / "config.yaml").read_text(encoding="utf-8"))
    cfg["input"].update({"db_path": str(db), **input_overrides})
    cfg["paths"]["processed_data"] = str(tmp_path / "out" / "issues_clean.jsonl")
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return path


def test_preprocess_reads_db_and_writes_outputs(make_db, tmp_path):
    db = make_db(
        items=[
            {"repo": "a/b", "number": 1, "title": "VQE fails", "body": "The optimizer does not converge on hardware.", "author": "u"},
            {"repo": "a/b", "number": 2, "type": "pr", "title": "A PR", "body": "should be ignored entirely"},
            {"repo": "a/b", "number": 3, "created_at": None},
        ],
        comments=[{"repo": "a/b", "item_number": 1, "author": "helper", "body": "Try increasing shots to 8192."}],
    )
    cfg = _config(tmp_path, db, max_reject_ratio=1.0)
    result = runner.invoke(app, ["preprocess", "--config", str(cfg)])
    assert result.exit_code == 0, result.output
    out = tmp_path / "out" / "issues_clean.jsonl"
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert [r["issue_number"] for r in rows] == [1]
    assert len(rows[0]["comments"]) == 1
    rej = (tmp_path / "out" / "rejections.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rej) == 1 and json.loads(rej[0])["reason"] == "bad_created_at"
    assert "bad_created_at" in result.output


def test_preprocess_fails_when_reject_ratio_exceeded(make_db, tmp_path):
    db = make_db(items=[{"repo": "a/b", "number": 1}, {"repo": "a/b", "number": 2, "created_at": None}])
    result = runner.invoke(app, ["preprocess", "--config", str(_config(tmp_path, db))])
    assert result.exit_code == 1
    assert "rejected" in result.output
