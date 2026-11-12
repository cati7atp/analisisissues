"""Main CLI entry point for quantum issues analysis."""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table

from .config import load_config, get_config
from .loader import LoadStats, RejectionRatioExceeded, load_items_sqlite
from .preprocess import IssuePreprocessor

app = typer.Typer(
    name="quantum-issues",
    help="Analyze GitHub issues from quantum software repositories",
    add_completion=False,
)
console = Console()


@app.command()
def preprocess(
    input_file: str = typer.Option(None, "--input", "-i", help="Legacy raw issues JSONL (default: read the SQLite dataset)"),
    db_file: str = typer.Option(None, "--db", help="miner.db path (overrides input.db_path)"),
    output_file: str = typer.Option(None, "--output", "-o", help="Output JSONL file for cleaned issues"),
    config_file: str = typer.Option("config.yaml", "--config", "-c", help="Config file path"),
):
    """Preprocess GitHub issues from the SQLite dataset (or a legacy JSONL) for analysis."""
    cfg = load_config(Path(config_file))
    preprocessor = IssuePreprocessor(cfg)
    output_path = Path(output_file) if output_file else cfg.paths.processed_data

    if input_file:
        input_path = Path(input_file)
        if not input_path.exists():
            console.print(f"[red]Input file not found: {input_path}[/red]")
            raise typer.Exit(1)
        stats = preprocessor.process(input_path, output_path)
        console.print(f"[green]Processed {stats['kept']} issues -> {output_path}[/green]")
        return

    if db_file:
        cfg.input.db_path = Path(db_file)
    if not cfg.input.db_path.exists():
        console.print(f"[red]Dataset not found: {cfg.input.db_path}[/red]")
        raise typer.Exit(1)

    load_stats = LoadStats()
    rejections_path = output_path.parent / "rejections.jsonl"
    passes = {"count": 0}

    def items():
        # pass 1 (counting) uses throwaway stats so loaded/rejection counts are not doubled
        passes["count"] += 1
        if passes["count"] == 1 and (cfg.preprocessing.repeated_line_min_issues > 0 or cfg.preprocessing.repeated_comment_min_issues > 0):
            return load_items_sqlite(cfg.input, LoadStats())
        return load_items_sqlite(cfg.input, load_stats, rejections_path)

    try:
        stats = preprocessor.process_items(items, output_path)
    except RejectionRatioExceeded as exc:
        console.print(f"[red]Too many rows rejected: {exc}[/red]")
        raise typer.Exit(1)

    console.print(f"loaded: {load_stats.loaded}")
    console.print(f"excluded (repos): {load_stats.excluded}")
    console.print(f"rejected: {load_stats.rejections.total} {dict(load_stats.rejections.by_reason)}")
    console.print(f"skipped (bot-authored issues): {stats['bot_issues']}")
    console.print(f"skipped (exact duplicates): {stats['duplicates']}")
    console.print(f"skipped (empty content): {stats['skipped'] - stats['bot_issues'] - stats['duplicates']}")
    console.print(f"repeated lines: {stats['repeated_lines']} distinct, {stats['repeated_line_removals']} removed")
    console.print(f"repeated comments: {stats['repeated_comments']} distinct, {stats['repeated_comment_drops']} dropped")
    console.print(f"[green]Processed {stats['kept']} issues -> {output_path}[/green]")


@app.command()
def topic_model(
    input_file: str = typer.Option(None, "--input", "-i", help="Input cleaned issues JSONL"),
    output_dir: str = typer.Option(None, "--output-dir", "-o", help="Output directory for the model, topics, doc-topic assignments and HTML"),
    min_topic_size: int = typer.Option(None, "--min-topic-size", help="Minimum topic size (sets bertopic.hdbscan_min_cluster_size)"),
    n_topics: int = typer.Option(None, "--n-topics", help="Target number of topics (None=auto)"),
    embedding_model: str = typer.Option(None, "--embedding-model", help="Sentence transformer model"),
    config_file: str = typer.Option("config.yaml", "--config", "-c", help="Config file path"),
):
    """Run BERTopic topic modeling on cleaned issues."""
    from .topic_model import run_topic_modeling
    
    cfg = load_config(Path(config_file))
    
    input_path = Path(input_file) if input_file else cfg.paths.processed_data
    output_path = Path(output_dir) if output_dir else cfg.paths.model_dir
    
    if not input_path.exists():
        console.print(f"[red]Input file not found: {input_path}[/red]")
        raise typer.Exit(1)
    
    if output_dir:
        # --output-dir redirects the model and every result file together
        cfg.paths.topics_output = output_path / cfg.paths.topics_output.name
        cfg.paths.doc_topics_output = output_path / cfg.paths.doc_topics_output.name
        cfg.paths.visualization_html = output_path / cfg.paths.visualization_html.name

    # Override config with CLI args
    if min_topic_size is not None:
        cfg.bertopic.hdbscan_min_cluster_size = min_topic_size
    if n_topics is not None:
        cfg.bertopic.nr_topics = n_topics
    if embedding_model is not None:
        cfg.bertopic.embedding_model = embedding_model
    
    run_topic_modeling(cfg, input_path, output_path)
    console.print(f"[green]Topic modeling complete. Results in {output_path}[/green]")


@app.command()
def extract_patterns(
    topics_file: str = typer.Option(None, "--topics", help="Topics JSONL file"),
    issues_file: str = typer.Option(None, "--issues", help="Cleaned issues JSONL file"),
    output_file: str = typer.Option(None, "--output", "-o", help="Output patterns JSONL"),
    config_file: str = typer.Option("config.yaml", "--config", "-c", help="Config file path"),
):
    """Extract quantum-specific patterns from topics and issues."""
    from .patterns import extract_quantum_patterns
    
    cfg = load_config(Path(config_file))
    
    topics_path = Path(topics_file) if topics_file else cfg.paths.topics_output
    issues_path = Path(issues_file) if issues_file else cfg.paths.processed_data
    output_path = Path(output_file) if output_file else cfg.paths.patterns_output
    
    if not topics_path.exists():
        console.print(f"[red]Topics file not found: {topics_path}[/red]")
        raise typer.Exit(1)
    if not issues_path.exists():
        console.print(f"[red]Issues file not found: {issues_path}[/red]")
        raise typer.Exit(1)
    
    patterns = extract_quantum_patterns(cfg, topics_path, issues_path, output_path)
    console.print(f"[green]Extracted {len(patterns)} patterns -> {output_path}[/green]")


@app.command()
def compute_metrics(
    issues_file: str = typer.Option(None, "--issues", help="Cleaned issues JSONL file"),
    patterns_file: str = typer.Option(None, "--patterns", help="Patterns JSONL file"),
    output_json: str = typer.Option(None, "--output-json", help="Output metrics JSON"),
    output_csv: str = typer.Option(None, "--output-csv", help="Output metrics CSV"),
    config_file: str = typer.Option("config.yaml", "--config", "-c", help="Config file path"),
):
    """Compute maintainability metrics from issues and patterns."""
    from .metrics import compute_maintainability_metrics
    
    cfg = load_config(Path(config_file))
    
    issues_path = Path(issues_file) if issues_file else cfg.paths.processed_data
    patterns_path = Path(patterns_file) if patterns_file else cfg.paths.patterns_output
    json_path = Path(output_json) if output_json else cfg.paths.metrics_output
    csv_path = Path(output_csv) if output_csv else cfg.paths.metrics_csv
    
    if not issues_path.exists():
        console.print(f"[red]Issues file not found: {issues_path}[/red]")
        raise typer.Exit(1)
    
    metrics = compute_maintainability_metrics(cfg, issues_path, patterns_path, json_path, csv_path)
    console.print(f"[green]Metrics computed -> {json_path}, {csv_path}[/green]")


@app.command()
def generate_report(
    metrics_file: str = typer.Option(None, "--metrics", help="Metrics JSON file"),
    topics_file: str = typer.Option(None, "--topics", help="Topics JSONL file"),
    patterns_file: str = typer.Option(None, "--patterns", help="Patterns JSONL file"),
    output_file: str = typer.Option(None, "--output", "-o", help="Output report Markdown"),
    anonymize: bool = typer.Option(True, "--anonymize/--no-anonymize", help="Anonymize repo names"),
    config_file: str = typer.Option("config.yaml", "--config", "-c", help="Config file path"),
):
    """Generate scientific report from analysis results."""
    from .report import generate_report
    
    cfg = load_config(Path(config_file))
    
    metrics_path = Path(metrics_file) if metrics_file else cfg.paths.metrics_output
    topics_path = Path(topics_file) if topics_file else cfg.paths.topics_output
    patterns_path = Path(patterns_file) if patterns_file else cfg.paths.patterns_output
    output_path = Path(output_file) if output_file else cfg.paths.report_md
    
    if not metrics_path.exists():
        console.print(f"[red]Metrics file not found: {metrics_path}[/red]")
        raise typer.Exit(1)
    
    generate_report(cfg, metrics_path, topics_path, patterns_path, output_path, anonymize)
    console.print(f"[green]Report generated -> {output_path}[/green]")


@app.command()
def run_pipeline(
    input_file: str = typer.Option(None, "--input", "-i", help="Input raw issues JSONL"),
    config_file: str = typer.Option("config.yaml", "--config", "-c", help="Config file path"),
    skip_preprocess: bool = typer.Option(False, "--skip-preprocess", help="Skip preprocessing step"),
):
    """Run the full analysis pipeline end-to-end."""
    cfg = load_config(Path(config_file))
    
    input_path = Path(input_file) if input_file else cfg.paths.raw_data
    
    if not input_path.exists():
        console.print(f"[red]Input file not found: {input_path}[/red]")
        raise typer.Exit(1)
    
    console.print("[bold]Starting full analysis pipeline...[/bold]")
    
    # Step 1: Preprocess
    if not skip_preprocess:
        console.print("[cyan]Step 1/5: Preprocessing...[/cyan]")
        preprocessor = IssuePreprocessor(cfg)
        preprocessor.process(input_path, cfg.paths.processed_data)
    else:
        console.print("[cyan]Step 1/5: Preprocessing skipped[/cyan]")
    
    # Step 2: Topic modeling
    console.print("[cyan]Step 2/5: Topic modeling...[/cyan]")
    from .topic_model import run_topic_modeling
    run_topic_modeling(cfg, cfg.paths.processed_data, cfg.paths.model_dir)
    
    # Step 3: Pattern extraction
    console.print("[cyan]Step 3/5: Pattern extraction...[/cyan]")
    from .patterns import extract_quantum_patterns
    extract_quantum_patterns(cfg, cfg.paths.topics_output, cfg.paths.processed_data, cfg.paths.patterns_output)
    
    # Step 4: Metrics
    console.print("[cyan]Step 4/5: Computing metrics...[/cyan]")
    from .metrics import compute_maintainability_metrics
    compute_maintainability_metrics(cfg, cfg.paths.processed_data, cfg.paths.patterns_output, cfg.paths.metrics_output, cfg.paths.metrics_csv)
    
    # Step 5: Report
    console.print("[cyan]Step 5/5: Generating report...[/cyan]")
    from .report import generate_report
    generate_report(cfg, cfg.paths.metrics_output, cfg.paths.topics_output, cfg.paths.patterns_output, cfg.paths.report_md, cfg.report.anonymize)
    
    console.print("[bold green]Pipeline complete![/bold green]")
    console.print(f"Report: {cfg.paths.report_md}")
    console.print(f"Visualization: {cfg.paths.visualization_html}")


@app.command()
def info():
    """Show configuration and paths."""
    cfg = get_config()
    
    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Raw data", str(cfg.paths.raw_data))
    table.add_row("Processed data", str(cfg.paths.processed_data))
    table.add_row("Topics output", str(cfg.paths.topics_output))
    table.add_row("Patterns output", str(cfg.paths.patterns_output))
    table.add_row("Metrics output", str(cfg.paths.metrics_output))
    table.add_row("Model dir", str(cfg.paths.model_dir))
    table.add_row("Report", str(cfg.paths.report_md))
    table.add_row("Embedding model", cfg.bertopic.embedding_model)
    table.add_row("Min topic size", str(cfg.bertopic.hdbscan_min_cluster_size))
    
    console.print(table)


if __name__ == "__main__":
    app()