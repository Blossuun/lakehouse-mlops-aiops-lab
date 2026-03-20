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

Write-Host "INFO: Running gold metrics build"
$rc = Invoke-SparkSubmit @(
  "/opt/lab/jobs/spark/build_gold_metrics.py",
  "--date", $Date
)

if ($rc -ne 0) {
  Write-Host "FAIL: gold metrics build failed (exit=$rc)"
  exit 10
}

Write-Host "OK: gold metrics build completed"
exit 0