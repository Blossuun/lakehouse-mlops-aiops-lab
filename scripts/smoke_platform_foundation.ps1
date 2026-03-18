param(
    [string]$ComposeFile = ".\infra\docker-compose.yml",
    [string]$EnvFile = ".\infra\.env"
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_workflow_common.ps1"

Require-Path -Path ".\scripts\bootstrap_local_platform.ps1" -Label "bootstrap_local_platform.ps1"
Require-Path -Path ".\scripts\smoke_shared_catalog_spark_trino.ps1" -Label "smoke_shared_catalog_spark_trino.ps1"

Invoke-Step "load environment variables from infra/.env" {
    Import-DotEnv -Path $EnvFile
}

Invoke-Step "bootstrap local platform" {
    powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_local_platform.ps1 -ComposeFile $ComposeFile -EnvFile $EnvFile
    if ($LASTEXITCODE -ne 0) {
        throw "bootstrap_local_platform.ps1 failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "verify MinIO connectivity" {
    uv run python .\scripts\smoke_minio.py | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_minio.py failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "verify MLflow connectivity" {
    uv run python .\scripts\smoke_mlflow.py | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_mlflow.py failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "verify shared Iceberg catalog (Spark write / Trino read)" {
    powershell -ExecutionPolicy Bypass -File .\scripts\smoke_shared_catalog_spark_trino.ps1
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_shared_catalog_spark_trino.ps1 failed with exit code $LASTEXITCODE"
    }
}

Write-Host ""
Write-Host "OK: platform foundation smoke passed" -ForegroundColor Green