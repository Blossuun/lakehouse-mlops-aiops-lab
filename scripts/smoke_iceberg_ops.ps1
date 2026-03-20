param(
  [string]$Date = "2026-02-27"
)

$ErrorActionPreference = "Stop"

. "$PSScriptRoot/lib/spark_smoke_common.ps1"

Write-SparkSmokeVersions
Initialize-SparkIvyCache

$rc = Initialize-SparkIvyCache
if ($rc -ne 0) {
  Write-Host "FAIL: could not prepare ivy cache directories inside container (exit=$rc)"
  exit 9
}

# 1) Inspect snapshots/history
Write-Host "INFO: 1) Inspect snapshots/history"
$rc = Invoke-SparkSubmit @("/opt/lab/jobs/spark/iceberg_inspect.py")
if ($rc -ne 0) {
  Write-Host "FAIL: inspect job failed (exit=$rc)"
  exit 10
}

# 2) Schema evolution
Write-Host "INFO: 2) Schema evolution (add column + verify)"
$rc = Invoke-SparkSubmit @(
  "/opt/lab/jobs/spark/iceberg_schema_evolution.py",
  "--date", $Date
)
if ($rc -ne 0) {
  Write-Host "FAIL: schema evolution failed (exit=$rc)"
  exit 11
}

# 3) Time travel demo
Write-Host "INFO: 3) Time travel demo"
$rc = Invoke-SparkSubmit @(
  "/opt/lab/jobs/spark/iceberg_time_travel.py",
  "--date", $Date
)
if ($rc -ne 0) {
  Write-Host "FAIL: time travel failed (exit=$rc)"
  exit 12
}

Write-Host "OK: smoke_iceberg_ops completed"
exit 0