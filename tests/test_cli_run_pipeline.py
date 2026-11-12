"""run-pipeline chains the individual commands over one output directory."""

from typer.testing import CliRunner

from src import cli

runner = CliRunner()


def test_run_pipeline_chains_every_step_with_one_output_dir(monkeypatch, tmp_path):
    calls = []

    def recorder(name):
        def fake(**kwargs):
            calls.append((name, kwargs))
        return fake

    for name in ("preprocess", "topic_model", "extract_patterns", "compute_metrics", "generate_report"):
        monkeypatch.setattr(cli, name, recorder(name))

    result = runner.invoke(cli.app, ["run-pipeline", "--db", "x.db", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert [c[0] for c in calls] == ["preprocess", "topic_model", "extract_patterns", "compute_metrics", "generate_report"]
    kwargs = dict(calls)
    assert kwargs["preprocess"]["db_file"] == "x.db"
    for step in ("topic_model", "extract_patterns", "compute_metrics"):
        assert kwargs[step]["output_dir"] == str(tmp_path)
    assert kwargs["generate_report"]["topics_file"] == str(tmp_path / "topics.jsonl")


def test_run_pipeline_skip_preprocess(monkeypatch, tmp_path):
    names = []
    for name in ("preprocess", "topic_model", "extract_patterns", "compute_metrics", "generate_report"):
        monkeypatch.setattr(cli, name, lambda _n=name, **kw: names.append(_n))
    result = runner.invoke(cli.app, ["run-pipeline", "--skip-preprocess", "--output-dir", str(tmp_path)])
    assert result.exit_code == 0 and "preprocess" not in names
