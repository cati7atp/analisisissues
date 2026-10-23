#!/bin/bash
set -e

echo "Starting quantum issues analysis pipeline..."

# Check if virtual environment exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Check input file
INPUT_FILE="${1:-data/raw/issues.jsonl}"
if [ ! -f "$INPUT_FILE" ]; then
    echo "ERROR: Input file not found: $INPUT_FILE" >&2
    echo "Please place your GitHub issues JSONL file at: $INPUT_FILE" >&2
    echo ""
    echo "Expected format (one JSON object per line):"
    echo '{"repo": "owner/repo", "issue_number": 123, "title": "...", "body": "...", "state": "open", "labels": ["bug"], "created_at": "2024-01-01T00:00:00Z", "closed_at": null, "author": "username", "comments": [{"author": "user", "created_at": "2024-01-01T00:00:00Z", "body": "..."}]}'
    exit 1
fi

# Run pipeline
python -m src.cli run-pipeline --input "$INPUT_FILE" --config config.yaml

if [ $? -eq 0 ]; then
    echo ""
    echo "Pipeline completed successfully!"
    echo "Report: reports/quantum_maintainability_report.md"
    echo "Visualization: reports/topic_visualization.html"
    echo "Metrics: data/analysis/maintainability_metrics.json"
else
    echo "Pipeline failed" >&2
    exit 1
fi