#!/bin/bash
set -e

echo "Starting quantum issues analysis pipeline..."

# Comprueba si existe el entorno virtual
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Comprueba el dataset (la ruta viene de config.yaml: input.db_path, o pasa --db)
DB_ARG=()
if [ -n "$1" ]; then DB_ARG=(--db "$1"); fi

# Ejecuta el pipeline
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