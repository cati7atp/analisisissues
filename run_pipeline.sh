#!/bin/bash
set -e

echo "Starting quantum issues analysis pipeline..."

# Check if virtual environment exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Check dataset (path comes from config.yaml: input.db_path, or pass --db)
DB_ARG=()
if [ -n "$1" ]; then DB_ARG=(--db "$1"); fi

# Run pipeline
python -m src.cli run-pipeline --config config.yaml "${DB_ARG[@]}"

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