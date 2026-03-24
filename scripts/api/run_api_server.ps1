$ErrorActionPreference = "Stop"

Write-Host "INFO: Starting read-only API server"
Write-Host "INFO: Make sure lab-trino is running and local port 8080 is reachable"

uv run --group api uvicorn apps.api_server:app --reload --port 8000
$rc = $LASTEXITCODE

if ($rc -ne 0) {
  Write-Host "FAIL: API server failed to start (exit=$rc)"
  exit 1
}

exit 0