param(
    [string]$ComposeFile = ".\infra\docker-compose.yml",
    [string]$EnvFile = ".\infra\.env"
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_workflow_common.ps1"

Invoke-Step "run platform foundation smoke" {
    powershell -ExecutionPolicy Bypass -File .\scripts\smoke_platform_foundation.ps1 -ComposeFile $ComposeFile -EnvFile $EnvFile
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_platform_foundation.ps1 failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "run analytics stack smoke" {
    powershell -ExecutionPolicy Bypass -File .\scripts\smoke_analytics_stack.ps1 -ComposeFile $ComposeFile -EnvFile $EnvFile
    if ($LASTEXITCODE -ne 0) {
        throw "smoke_analytics_stack.ps1 failed with exit code $LASTEXITCODE"
    }
}

Write-Host ""
Write-Host "OK: default smoke path passed" -ForegroundColor Green