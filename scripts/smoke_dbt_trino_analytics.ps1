param(
    [string]$Date = "2026-02-27",
    [string]$ComposeFile = ".\infra\docker-compose.yml",
    [string]$EnvFile = ".\infra\.env",
    [string]$DbtProfilesDir = ".\analytics\profiles",
    [string]$TrinoContainer = "lab-trino"
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

function Read-DotEnv {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        throw "Env file not found: $Path"
    }

    $map = @{}

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()

        if (-not $line) { return }
        if ($line.StartsWith("#")) { return }
        if ($line -notmatch "=") { return }

        $parts = $line -split "=", 2
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()

        if ($value.StartsWith('"') -and $value.EndsWith('"')) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        $map[$key] = $value
    }

    return $map
}

if (-not (Test-Path $ComposeFile)) {
    throw "Compose file not found: $ComposeFile"
}

if (-not (Test-Path ".\scripts\render_dbt_profile.ps1")) {
    throw "render_dbt_profile.ps1 not found"
}

$envMap = Read-DotEnv -Path $EnvFile

if (-not $envMap.ContainsKey("TRINO_CATALOG")) {
    throw "TRINO_CATALOG is missing in $EnvFile"
}

$catalog = $envMap["TRINO_CATALOG"]
$profilesDirPath = (Resolve-Path $DbtProfilesDir).Path

Invoke-Step "render dbt profile" {
    powershell -ExecutionPolicy Bypass -File .\scripts\render_dbt_profile.ps1 -EnvFile $EnvFile
}

Invoke-Step "ensure trino is running" {
    docker compose -f $ComposeFile up -d trino | Out-Host
}

Invoke-Step "build staging and marts" {
    $env:DBT_PROFILES_DIR = $profilesDirPath
    Push-Location .\analytics
    try {
        uv run dbt run --select stg_silver_events marts
        uv run dbt test --select stg_silver_events marts
    }
    finally {
        Pop-Location
    }
}

Invoke-Step "verify mart row counts in trino" {
    docker exec -i $TrinoContainer trino --execute "select count(*) as row_count from $catalog.analytics.fct_daily_events" | Out-Host
    docker exec -i $TrinoContainer trino --execute "select count(*) as row_count from $catalog.analytics.fct_daily_revenue" | Out-Host
    docker exec -i $TrinoContainer trino --execute "select count(*) as row_count from $catalog.analytics.fct_daily_conversion" | Out-Host
}

Invoke-Step "verify mart contents in trino" {
    docker exec -i $TrinoContainer trino --execute "select * from $catalog.analytics.fct_daily_events order by event_date" | Out-Host
    docker exec -i $TrinoContainer trino --execute "select * from $catalog.analytics.fct_daily_revenue order by event_date" | Out-Host
    docker exec -i $TrinoContainer trino --execute "select * from $catalog.analytics.fct_daily_conversion order by event_date" | Out-Host
}

Write-Host ""
Write-Host "OK: dbt-trino analytics smoke passed" -ForegroundColor Green