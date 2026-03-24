$ErrorActionPreference = "Stop"

Write-Host "INFO: Starting analysis dashboard"
Write-Host "INFO: Make sure lab-trino is running and local port 8080 is reachable"

uv run --group dashboard streamlit run .\apps\analysis_dashboard.py
$rc = $LASTEXITCODE

if ($rc -ne 0) {
  Write-Host "FAIL: dashboard failed to start (exit=$rc)"
  exit 1
}

exit 0