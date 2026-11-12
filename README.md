# Quantum GitHub Issues Analysis

A Python pipeline for analyzing GitHub issues from repositories using quantum computing components (Qiskit, Cirq, PennyLane, Amazon Braket, Q#, etc.) to identify maintainability patterns in hybrid quantum-classical software products.

## Overview

This project addresses a critical gap in software engineering research: understanding the maintainability challenges of hybrid quantum-classical systems, which are still a novelty in the industry. By applying NLP topic modeling (BERTopic) and domain-specific pattern extraction to GitHub issues, we identify common failure modes, quantify their prevalence, and provide actionable recommendations for practitioners.

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Prepare Input Data

Place your GitHub issues data as a JSONL file at `data/raw/issues.jsonl`. Each line should be a JSON object:

```json
{
  "repo": "owner/repo",
  "issue_number": 123,
  "title": "Issue title",
  "body": "Issue body text",
  "state": "open",
  "labels": ["bug", "quantum"],
  "created_at": "2024-01-15T10:30:00Z",
  "closed_at": null,
  "author": "username",
  "comments": [
    {
      "author": "commenter",
      "created_at": "2024-01-16T12:00:00Z",
      "body": "Comment text"
    }
  ],
  "assignees": [],
  "milestone": null,
  "reactions": {"+1": 5}
}
```

### 3. Run the Pipeline

```bash
# Run full pipeline
python -m src.cli run-pipeline   # reads input.db_path (miner.db); --db PATH overrides it, --output-dir DIR redirects every output

# Or step by step:
python -m src.cli preprocess   # reads input.db_path (miner.db); --input still accepts a legacy JSONL
python -m src.cli topic-model
python -m src.cli extract-patterns   # --output-dir DIR reads the topic results from DIR and writes patterns and cross_project_patterns.* there
python -m src.cli compute-metrics   # --output-dir DIR writes metrics, CSV and comparisons.json there
python -m src.cli generate-report
```

### 4. View Results

- **Report**: `reports/quantum_maintainability_report.md`
- **Visualization**: `reports/topic_visualization.html` (open in browser)
- **Metrics**: `data/analysis/maintainability_metrics.json`
- **Patterns**: `data/analysis/quantum_patterns.jsonl`
- **Cross-project patterns**: `data/analysis/cross_project_patterns.csv` (a topic is cross-project when `cross_project.min_repos` repos each hold `min_issues_per_repo` of its issues and no repo exceeds `max_top_repo_share`)

## Pipeline Stages

| Stage | Command | Output | Description |
|-------|---------|--------|-------------|
| 1. Preprocess | `preprocess` | `data/processed/issues_clean.jsonl` | Clean, normalize, classify issues |
| 2. Topic Model | `topic-model` | `data/analysis/topics.jsonl` | BERTopic topic discovery |
| 3. Patterns | `extract-patterns` | `data/analysis/quantum_patterns.jsonl` | Quantum-specific pattern extraction |
| 4. Metrics | `compute-metrics` | `data/analysis/maintainability_metrics.json` | Maintainability indicators |
| 5. Report | `generate-report` | `reports/quantum_maintainability_report.md` | Scientific report |

## Configuration

All parameters are configurable via `config.yaml`:

- **Preprocessing**: Bot filtering by author (`author_type` Bot, `[bot]` suffix or exact names in `bot_users`), anchored `automated_comment_patterns` for template comments, min body length, code fence stripping; code, traceback and build-log summaries, template stripping (`strip_templates`), and a two-pass filter that removes lines seen in at least `repeated_line_min_issues` distinct issues and drops comments seen in at least `repeated_comment_min_issues` distinct issues; exact duplicate documents are dropped (`drop_exact_duplicates`, first occurrence kept); issues with fewer than `min_chars` cleaned title+body characters are skipped
- **BERTopic**: Embedding model, UMAP/HDBSCAN parameters, min cluster size (`--min-topic-size` sets `hdbscan_min_cluster_size`), `reproducible` (seeds UMAP), embeddings computed once and cached under `paths.cache_dir` (`embed_*` options; run summary with outlier share and `outcome` in the model dir; 0 or 1 clusters end with `outcome: no_topics` and empty outputs instead of an error), optional `reduce_outliers` (off by default; writes separate `*_reduced` outputs), vectorizer `min_df`/`max_df` (fraction of topics) and `domain_stop_words`
- **Quantum Patterns**: 8 categories with 50+ keywords (extensible)
- **Metrics**: Gini computation, resolution quantiles
- **Report**: Anonymization, quote limits

## Quantum Pattern Taxonomy

| Category | Description | Example Keywords |
|----------|-------------|------------------|
| Hardware/Backend | Device availability, calibration, queue times | noise, calibration, queue, backend |
| Algorithm Convergence | Variational algorithm issues | VQE, QAOA, ansatz, barren plateau |
| Dependency/Version | Framework version conflicts | qiskit-terra, numpy, version conflict |
| Simulator vs Hardware | Discrepancies between sim and real | simulator, hardware, noise model |
| Transpilation/Compilation | Circuit compilation failures | transpile, coupling map, routing |
| Gradients/Autodiff | Differentiation failures | gradient, parameter-shift, adjoint |
| Reproducibility | Non-deterministic results | seed, deterministic, random |
| Performance/Scaling | Large circuit performance | scaling, qubit count, depth |

## Extending Pattern Categories

Categories and their keywords live in `config/quantum_taxonomy.yaml` (the `quantum_patterns` block of `config.yaml` is legacy and ignored).

## Running Tests

```bash
pytest -q
pytest --cov=src tests/
```

## Project Structure

```
quantum-issues-analysis/
├── src/
│   ├── __init__.py
│   ├── cli.py              # Typer CLI entry point
│   ├── config.py           # Configuration management
│   ├── models.py           # Pydantic data models
│   ├── preprocess.py       # S3: Data preprocessing
│   ├── topic_model.py      # S4: BERTopic modeling
│   ├── patterns.py         # S5: Quantum pattern extraction
│   ├── metrics.py          # S6: Maintainability metrics
│   └── report.py           # S7: Report generation
├── tests/
├── data/
│   ├── raw/                # Input: issues.jsonl
│   ├── processed/          # Cleaned issues
│   └── analysis/           # Topics, patterns, metrics
├── models/
│   └── bertopic/           # Saved BERTopic model (model/ = safetensors; --output-dir redirects model and results)
├── reports/
│   ├── quantum_maintainability_report.md
│   ├── topic_visualization.html
│   └── *.csv               # Summary tables
├── odd/
│   └── tasks/              # ODD feature specification
├── .github/
│   └── workflows/          # GitHub Actions
├── config.yaml
├── requirements.txt
├── pyproject.toml
├── run_pipeline.sh
├── run_pipeline.ps1
└── README.md
```

## License

MIT

## Citation

If you use this work in research, please cite:

```bibtex
@misc{quantum-issues-analysis,
  title={Quantum Software Maintainability Analysis via GitHub Issue Mining},
  year={2024},
  note={Analysis of hybrid quantum-classical software maintainability patterns}
}
```