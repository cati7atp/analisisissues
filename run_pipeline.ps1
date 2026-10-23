# Quantum GitHub Issues Analysis - Pipeline Runner

Write-Host "Starting quantum issues analysis pipeline..." -ForegroundColor Cyan

# Check if virtual environment exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
}

# Check input file
$inputFile = "data/raw/issues.jsonl"
if (-not (Test-Path $inputFile)) {
    Write-Host "ERROR: Input file not found: $inputFile" -ForegroundColor Red
    Write-Host "Please place your GitHub issues JSONL file at: $inputFile" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Expected format (one JSON object per line):" -ForegroundColor Yellow
    Write-Host '{"repo": "owner/repo", "issue_number": 123, "title": "...", "body": "...", "state": "open", "labels": ["bug"], "created_at": "2024-01-01T00:00:00Z", "closed_at": null, "author": "username", "comments": [{"author": "user", "created_at": "2024-01-01T00:00:00Z", "body": "..."}]}' -ForegroundColor Gray
    exit 1
}

# Run pipeline
python -m src.cli run-pipeline --input $inputFile --config config.yaml

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