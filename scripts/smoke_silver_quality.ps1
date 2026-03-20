param(
  [string]$Date = "2026-02-27"
)

$ErrorActionPreference = "Stop"

. "$PSScriptRoot/lib/spark_smoke_common.ps1"

$ReportOut = "s3a://datalake/audit/quality_checks/dt=$Date"

Write-SparkSmokeVersions
Initialize-SparkIvyCache

$rc = Initialize-SparkIvyCache
if ($rc -ne 0) {
  Write-Host "FAIL: could not prepare ivy cache directories inside container (exit=$rc)"
  exit 9
}

Write-Host "INFO: Running quality gate"
$rc = Invoke-SparkSubmit @(
  "/opt/lab/jobs/spark/check_silver_quality.py",
  "--date", $Date,
  "--report-out", $ReportOut
)

if ($rc -ne 0) {
  Write-Host "FAIL: silver quality gate failed (exit=$rc)"
  exit 10
}

Write-Host "OK: silver quality gate passed"
Write-Host "INFO: report written to $ReportOut"
exit 0