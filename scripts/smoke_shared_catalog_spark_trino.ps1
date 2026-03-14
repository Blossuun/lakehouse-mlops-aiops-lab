$ErrorActionPreference = "Stop"

Write-Host "INFO: Preparing Hive cache"
& "$PSScriptRoot\prepare_hive_cache.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Hive cache preparation failed"
    exit 1
}

Write-Host "INFO: Rendering catalog configs"
& "$PSScriptRoot\render_catalog_configs.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: catalog config rendering failed"
    exit 1
}

$ICEBERG_VERSION = "1.6.0"
$HADOOP_AWS_VERSION = "3.3.4"
$PACKAGES = "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:$ICEBERG_VERSION,org.apache.hadoop:hadoop-aws:$HADOOP_AWS_VERSION"

Write-Host "INFO: Checking required containers"
$required = @("lab-spark", "lab-trino", "lab-hive-metastore", "lab-minio", "lab-postgres")

$running = docker ps --format "{{.Names}}"
foreach ($name in $required) {
    if (-not ($running -match $name)) {
        Write-Host "FAIL: required container '$name' is not running"
        exit 2
    }
}

Write-Host "INFO: Preparing Ivy cache in Spark container"
docker exec -u 0 -it lab-spark bash -lc "mkdir -p /tmp/.ivy2/cache /tmp/.ivy2/jars && chown -R 185:185 /tmp/.ivy2"
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: could not prepare Ivy cache directories"
    exit 3
}

Write-Host "INFO: Running Spark write smoke job"
docker exec -it lab-spark /opt/spark/bin/spark-submit `
  --conf spark.jars.ivy=/tmp/.ivy2 `
  --packages $PACKAGES `
  /opt/lab/jobs/spark/shared_catalog_write_smoke.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Spark shared catalog write smoke failed"
    exit 4
}

Write-Host "INFO: Running Trino read smoke query"
$result = docker exec -it lab-trino trino --output-format CSV_HEADER_UNQUOTED --execute "SELECT count(*) AS row_count FROM iceberg.test.catalog_smoke"

if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Trino shared catalog read smoke failed"
    exit 5
}

Write-Host $result

$lines = $result -split "`r?`n" | Where-Object { $_.Trim() -ne "" }
if ($lines.Count -lt 2) {
    Write-Host "FAIL: could not parse Trino row count output"
    exit 6
}

$rowCount = [int]$lines[1].Trim()
if ($rowCount -ne 2) {
    Write-Host "FAIL: expected row count = 2, but got $rowCount"
    exit 7
}

Write-Host "OK: Shared Iceberg catalog smoke passed"
exit 0