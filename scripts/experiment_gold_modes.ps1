param(
  [string]$Date = "2026-02-27",
  [string]$RunId = (Get-Date -Format "yyyyMMdd-HHmmss")
)

$ErrorActionPreference = "Stop"

. "$PSScriptRoot/lib/spark_smoke_common.ps1"

$hostOutDir = ".\tmp\gold_mode_experiments\$RunId"
$containerOutDir = "/tmp/gold_mode_experiments/$RunId"
$metricsFile = "$containerOutDir/results.csv"

function Drop-GoldTables {
  $dropStatements = @(
    "DROP TABLE IF EXISTS iceberg.gold.daily_event_metrics",
    "DROP TABLE IF EXISTS iceberg.gold.daily_revenue_metrics",
    "DROP TABLE IF EXISTS iceberg.gold.daily_conversion_metrics"
  )

  foreach ($sql in $dropStatements) {
    $cmd = @("docker", "exec", "-i", "lab-trino", "trino", "--execute", $sql)
    Write-Host "INFO: Running:"
    Write-Host ("  " + ($cmd -join " "))
    & $cmd[0] $cmd[1..($cmd.Length-1)] | Out-Host
    if ($LASTEXITCODE -ne 0) {
      Write-Host "FAIL: could not reset gold tables"
      exit 20
    }
  }
}

function Prepare-ContainerOutputDir {
  $cmd = @(
    "docker", "exec", "-i", "lab-spark",
    "bash", "-lc",
    "mkdir -p $containerOutDir && ls -ld $containerOutDir"
  )

  Write-Host "INFO: Preparing container output directory"
  Write-Host ("  " + ($cmd -join " "))

  & $cmd[0] $cmd[1..($cmd.Length-1)] | Out-Host
  if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: could not prepare container output directory"
    exit 21
  }
}

function Copy-ResultsToHost {
  $hostResults = Join-Path $hostOutDir "results.csv"
  $containerSource = "lab-spark:$metricsFile"

  $cmd = @("docker", "cp", $containerSource, $hostResults)

  Write-Host "INFO: Copying experiment results to host"
  Write-Host ("  " + ($cmd -join " "))

  & $cmd[0] $cmd[1..($cmd.Length-1)] | Out-Host
  if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: could not copy experiment results to host"
    exit 22
  }
}

New-Item -ItemType Directory -Force -Path $hostOutDir | Out-Null

Write-SparkSmokeVersions

$rc = Initialize-SparkIvyCache
if ($rc -ne 0) {
  Write-Host "FAIL: could not prepare ivy cache directories inside container (exit=$rc)"
  exit 9
}

Prepare-ContainerOutputDir

$modes = @("single-pass", "with-cache", "multi-pass")

foreach ($mode in $modes) {
  Write-Host ""
  Write-Host "INFO: ===== mode=$mode ====="

  Drop-GoldTables

  $rc = Invoke-SparkSubmit @(
    "/opt/lab/jobs/spark/build_gold_metrics.py",
    "--date", $Date,
    "--mode", $mode,
    "--metrics-out", $metricsFile
  )

  if ($rc -ne 0) {
    Write-Host "FAIL: gold experiment failed for mode=$mode (exit=$rc)"
    exit 30
  }
}

Copy-ResultsToHost

Write-Host ""
Write-Host "OK: gold experiment completed"
Write-Host "INFO: results saved to $hostOutDir\results.csv"
exit 0