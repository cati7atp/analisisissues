# Quantum GitHub Issues Analysis - Pipeline Runner

Write-Host "Starting quantum issues analysis pipeline..." -ForegroundColor Cyan

# Check if virtual environment exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
}

# Dataset path comes from config.yaml (input.db_path); pass a miner.db path to override it
$dbArgs = @()
if ($args.Count -gt 0) { $dbArgs = @("--db", $args[0]) }

# Run pipeline
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