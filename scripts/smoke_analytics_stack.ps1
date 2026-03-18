param(
    [string]$ComposeFile = ".\infra\docker-compose.yml",
    [string]$EnvFile = ".\infra\.env"
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_workflow_common.ps1"

Require-Path -Path ".\scripts\bootstrap_local_platform.ps1" -Label "bootstrap_local_platform.ps1"
Require-Path -Path ".\scripts\smoke_dbt_trino_analytics.ps1" -Label "smoke_dbt_trino_analytics.ps1"

Invoke-Step "load environment variables from infra/.env" {
    Import-DotEnv -Path $EnvFile
}

Invoke-Step "bootstrap local platform" {
    powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_local_platform.ps1 -ComposeFile $ComposeFile -EnvFile $EnvFile
    if ($LASTEXITCODE -ne 0) {
        throw "bootstrap_local_platform.ps1 failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "verify dbt + Trino analytics layer" {
    powershell -ExecutionPolicy Bypass -File .\scripts\smoke_dbt_trino_analytics.ps1
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_dbt_trino_analytics.ps1 failed with exit code $LASTEXITCODE"
    }
}

Write-Host ""
Write-Host "OK: analytics stack smoke passed" -ForegroundColor Green