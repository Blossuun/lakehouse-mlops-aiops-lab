param(
  [string]$Date = "2026-02-27"
)

$ErrorActionPreference = "Stop"

$ICEBERG_VERSION = "1.6.0"
$HADOOP_AWS_VERSION = "3.3.4"

Write-Host "INFO: Using pinned versions ICEBERG=$ICEBERG_VERSION, HADOOP_AWS=$HADOOP_AWS_VERSION"

$PACKAGES = "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:$ICEBERG_VERSION,org.apache.hadoop:hadoop-aws:$HADOOP_AWS_VERSION"

function Run-SparkSubmit {
  param(
    [Parameter(Mandatory=$true)]
    [string[]]$AppArgs
  )

  $baseArgs = @(
    "/opt/spark/bin/spark-submit",
    "--conf", "spark.jars.ivy=/tmp/ivy2",
    "--packages", $PACKAGES
  )

  $cmd = @("docker", "exec", "-i", "lab-spark") + $baseArgs + $AppArgs

  Write-Host "INFO: Running:"
  Write-Host ("  " + ($cmd -join " "))

  & $cmd[0] $cmd[1..($cmd.Length-1)] | Out-Host

  $exitCode = $LASTEXITCODE
  return [int]$exitCode
}

# 1) Inspect snapshots/history
Write-Host "INFO: 1) Inspect snapshots/history"
$rc = Run-SparkSubmit @("/opt/lab/jobs/spark/iceberg_inspect.py")
if ($rc -ne 0) {
  Write-Host "FAIL: inspect job failed (exit=$rc)"
  exit 10
}

# 2) Schema evolution
Write-Host "INFO: 2) Schema evolution (add column + verify)"
$rc = Run-SparkSubmit @("/opt/lab/jobs/spark/iceberg_schema_evolution.py", "--date", $Date)
if ($rc -ne 0) {
  Write-Host "FAIL: schema evolution failed (exit=$rc)"
  exit 11
}

# 3) Time travel demo
Write-Host "INFO: 3) Time travel demo"
$rc = Run-SparkSubmit @("/opt/lab/jobs/spark/iceberg_time_travel.py", "--date", $Date)
if ($rc -ne 0) {
  Write-Host "FAIL: time travel failed (exit=$rc)"
  exit 12
}

Write-Host "OK: smoke_iceberg_ops completed"
exit 0