param(
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

function Require-Path {
    param(
        [string]$Path,
        [string]$Label
    )

    if (-not (Test-Path $Path)) {
        throw "$Label not found: $Path"
    }
}

function Wait-ForContainer {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [int]$TimeoutSeconds = 90
    )

    $start = Get-Date
    while ($true) {
        $status = docker inspect -f "{{.State.Status}}" $Name 2>$null
        if ($LASTEXITCODE -eq 0 -and $status -eq "running") {
            return
        }

        if (((Get-Date) - $start).TotalSeconds -ge $TimeoutSeconds) {
            throw "Container '$Name' did not reach running state within $TimeoutSeconds seconds."
        }

        Start-Sleep -Seconds 2
    }
}

Require-Path -Path $ComposeFile -Label "Compose file"
Require-Path -Path $EnvFile -Label "Env file"
Require-Path -Path ".\scripts\prepare_hive_cache.ps1" -Label "prepare_hive_cache.ps1"
Require-Path -Path ".\scripts\render_catalog_configs.ps1" -Label "render_catalog_configs.ps1"
Require-Path -Path ".\scripts\render_dbt_profile.ps1" -Label "render_dbt_profile.ps1"

Invoke-Step "prepare hive dependency cache" {
    powershell -ExecutionPolicy Bypass -File .\scripts\prepare_hive_cache.ps1
}

Invoke-Step "render shared catalog configs" {
    powershell -ExecutionPolicy Bypass -File .\scripts\render_catalog_configs.ps1
}

Invoke-Step "render dbt profile" {
    powershell -ExecutionPolicy Bypass -File .\scripts\render_dbt_profile.ps1 -EnvFile $EnvFile
}

Invoke-Step "start local platform containers" {
    docker compose -f $ComposeFile --env-file $EnvFile up -d | Out-Host
}

$requiredContainers = @(
    "lab-minio",
    "lab-postgres",
    "lab-mlflow",
    "lab-spark",
    "lab-hive-metastore",
    "lab-trino"
)

Invoke-Step "wait for required containers to be running" {
    foreach ($name in $requiredContainers) {
        Wait-ForContainer -Name $name
        Write-Host "OK: $name is running" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "OK: local platform bootstrap completed" -ForegroundColor Green