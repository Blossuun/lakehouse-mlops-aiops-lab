$ErrorActionPreference = "Stop"

function Invoke-TaskOrFail {
  param(
    [Parameter(Mandatory = $true)]
    [string]$TaskName
  )

  task $TaskName

  if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: task '$TaskName' failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
  }
}

Write-Host "INFO: Starting full system validation"

Invoke-TaskOrFail "raw"
Invoke-TaskOrFail "silver"
Invoke-TaskOrFail "iceberg"
Invoke-TaskOrFail "iceberg:ops"
Invoke-TaskOrFail "quality"
Invoke-TaskOrFail "gold"

Write-Host "INFO: Validating query layer"

powershell -ExecutionPolicy Bypass -File .\scripts\query\run_trino_query.ps1 -QueryFile .\analytics\queries\daily_business_overview.sql
if ($LASTEXITCODE -ne 0) {
  Write-Host "FAIL: Trino query failed"
  exit 20
}

Write-Host "INFO: Validating API layer"

try {
  $response = Invoke-RestMethod -Uri "http://localhost:8000/metrics/overview?date=2026-02-27"
} catch {
  Write-Host "FAIL: API not reachable"
  exit 21
}

if (-not $response) {
  Write-Host "FAIL: API returned empty response"
  exit 22
}

Write-Host "OK: end-to-end validation passed"
exit 0