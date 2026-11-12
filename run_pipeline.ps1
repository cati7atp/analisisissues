# Ejecutor del pipeline completo de análisis.
# Uso: .\run_pipeline.ps1 [ruta\a\miner.db]
# Sin argumento, usa input.db_path de config.yaml.

# Trabaja siempre desde la raíz del repo, sin importar desde dónde se invoque.
Push-Location -LiteralPath $PSScriptRoot
try {
    # Activa el entorno virtual del proyecto (.venv, con venv como alternativa).
    $activate = @(".venv\Scripts\Activate.ps1", "venv\Scripts\Activate.ps1") |
        Where-Object { Test-Path $_ } |
        Select-Object -First 1

    if (-not $activate) {
        Write-Host "No se encontró un entorno virtual (.venv ni venv)." -ForegroundColor Red
        Write-Host "Creálo con:" -ForegroundColor Yellow
        Write-Host "  python -m venv .venv" -ForegroundColor Yellow
        Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
        Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
        exit 1
    }

    & $activate

    Write-Host "Iniciando el pipeline de análisis..." -ForegroundColor Cyan

    # La ruta del dataset viene de config.yaml (input.db_path); un argumento la reemplaza.
    $dbArgs = @()
    if ($args.Count -gt 0) { $dbArgs = @("--db", $args[0]) }

    python -m src.cli run-pipeline --config config.yaml @dbArgs

    if ($LASTEXITCODE -ne 0) {
        Write-Host "El pipeline falló con código $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }

    # run-pipeline escribe todo en el directorio de resultados; solo el reporte va a reports/.
    Write-Host ""
    Write-Host "Pipeline completado." -ForegroundColor Green
    Write-Host "Reporte:        reports/quantum_maintainability_report.md" -ForegroundColor Cyan
    Write-Host "Resultados:     data/analysis/" -ForegroundColor Cyan
    Write-Host "Visualización:  data/analysis/topic_visualization.html" -ForegroundColor Cyan
    Write-Host "Métricas:       data/analysis/maintainability_metrics.json" -ForegroundColor Cyan
}
finally {
    Pop-Location
}
