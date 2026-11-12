# Análisis de issues cuánticos de GitHub - Ejecutor del pipeline

Write-Host "Starting quantum issues analysis pipeline..." -ForegroundColor Cyan

# Comprueba si existe el entorno virtual
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
}

# La ruta del dataset viene de config.yaml (input.db_path); pasa una ruta a miner.db para reemplazarla
$dbArgs = @()
if ($args.Count -gt 0) { $dbArgs = @("--db", $args[0]) }

# Ejecuta el pipeline
python -m src.cli run-pipeline --config config.yaml @dbArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Pipeline completed successfully!" -ForegroundColor Green
    Write-Host "Report: reports/quantum_maintainability_report.md" -ForegroundColor Cyan
    Write-Host "Visualization: reports/topic_visualization.html" -ForegroundColor Cyan
    Write-Host "Metrics: data/analysis/maintainability_metrics.json" -ForegroundColor Cyan
} else {
    Write-Host "Pipeline failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}