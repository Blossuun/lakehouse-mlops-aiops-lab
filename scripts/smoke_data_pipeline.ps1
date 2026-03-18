param(
    [string]$Date = "2026-02-27",
    [string]$ComposeFile = ".\infra\docker-compose.yml",
    [string]$EnvFile = ".\infra\.env"
)

$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [string]$Message,
        [scriptblock]$Action
    )

    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
    & $Action
}

if (-not (Test-Path ".\scripts\bootstrap_local_platform.ps1")) {
    throw "bootstrap_local_platform.ps1 not found"
}

Invoke-Step "bootstrap local platform" {
    powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_local_platform.ps1 -ComposeFile $ComposeFile -EnvFile $EnvFile
}

Invoke-Step "run raw ingest smoke" {
    $env:RAW_DATE = $Date
    uv run python .\scripts\smoke_raw_ingest.py | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_raw_ingest.py failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "run silver transform smoke" {
    $env:SILVER_DATE = $Date
    uv run python .\scripts\smoke_silver_transform.py | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_silver_transform.py failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "load Silver into Iceberg" {
    powershell -ExecutionPolicy Bypass -File .\scripts\smoke_iceberg_table.ps1 -Date $Date
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_iceberg_table.ps1 failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "run Iceberg ops smoke" {
    powershell -ExecutionPolicy Bypass -File .\scripts\smoke_iceberg_ops.ps1 -Date $Date
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_iceberg_ops.ps1 failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "run Silver quality gate" {
    powershell -ExecutionPolicy Bypass -File .\scripts\smoke_silver_quality.ps1 -Date $Date
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_silver_quality.ps1 failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "build Gold metrics" {
    powershell -ExecutionPolicy Bypass -File .\scripts\smoke_gold_metrics.ps1 -Date $Date
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_gold_metrics.ps1 failed with exit code $LASTEXITCODE"
    }
}

Write-Host ""
Write-Host "OK: data pipeline smoke passed" -ForegroundColor Greenparam(
    [string]$Date = "2026-02-27",
    [string]$ComposeFile = ".\infra\docker-compose.yml",
    [string]$EnvFile = ".\infra\.env"
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_workflow_common.ps1"

Require-Path -Path ".\scripts\bootstrap_local_platform.ps1" -Label "bootstrap_local_platform.ps1"

Invoke-Step "load environment variables from infra/.env" {
    Import-DotEnv -Path $EnvFile
}

Invoke-Step "bootstrap local platform" {
    powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_local_platform.ps1 -ComposeFile $ComposeFile -EnvFile $EnvFile
    if ($LASTEXITCODE -ne 0) {
        throw "bootstrap_local_platform.ps1 failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "run raw ingest smoke" {
    $env:RAW_DATE = $Date
    uv run python .\scripts\smoke_raw_ingest.py | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_raw_ingest.py failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "run silver transform smoke" {
    $env:SILVER_DATE = $Date
    uv run python .\scripts\smoke_silver_transform.py | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_silver_transform.py failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "load Silver into Iceberg" {
    powershell -ExecutionPolicy Bypass -File .\scripts\smoke_iceberg_table.ps1 -Date $Date
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_iceberg_table.ps1 failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "run Iceberg ops smoke" {
    powershell -ExecutionPolicy Bypass -File .\scripts\smoke_iceberg_ops.ps1 -Date $Date
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_iceberg_ops.ps1 failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "run Silver quality gate" {
    powershell -ExecutionPolicy Bypass -File .\scripts\smoke_silver_quality.ps1 -Date $Date
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_silver_quality.ps1 failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "build Gold metrics" {
    powershell -ExecutionPolicy Bypass -File .\scripts\smoke_gold_metrics.ps1 -Date $Date
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_gold_metrics.ps1 failed with exit code $LASTEXITCODE"
    }
}

Write-Host ""
Write-Host "OK: data pipeline smoke passed" -ForegroundColor Green