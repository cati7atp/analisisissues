#!/bin/bash
# Ejecutor del pipeline completo de análisis.
# Uso: ./run_pipeline.sh [ruta/a/miner.db]
# Sin argumento, usa input.db_path de config.yaml.

set -euo pipefail

# Trabaja siempre desde la raíz del repo, sin importar desde dónde se invoque.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activa el entorno virtual del proyecto (.venv, con venv como alternativa).
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "No se encontró un entorno virtual (.venv ni venv)." >&2
    echo "Creálo con:" >&2
    echo "  python -m venv .venv" >&2
    echo "  source .venv/bin/activate" >&2
    echo "  pip install -r requirements.txt" >&2
    exit 1
fi

echo "Iniciando el pipeline de análisis..."

# La ruta del dataset viene de config.yaml (input.db_path); un argumento la reemplaza.
DB_ARG=()
if [ -n "${1:-}" ]; then DB_ARG=(--db "$1"); fi

if ! python -m src.cli run-pipeline --config config.yaml ${DB_ARG[@]+"${DB_ARG[@]}"}; then
    echo "El pipeline falló." >&2
    exit 1
fi

# run-pipeline escribe todo en el directorio de resultados; solo el reporte va a reports/.
echo ""
echo "Pipeline completado."
echo "Reporte:        reports/quantum_maintainability_report.md"
echo "Resultados:     data/analysis/"
echo "Visualización:  data/analysis/topic_visualization.html"
echo "Métricas:       data/analysis/maintainability_metrics.json"
