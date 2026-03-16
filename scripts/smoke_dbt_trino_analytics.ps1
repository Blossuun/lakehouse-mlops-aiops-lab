param(
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

$requiredKeys = @(
    "TRINO_CATALOG",
    "TRINO_SCHEMA"
)

foreach ($key in $requiredKeys) {
    if (-not $envMap.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($envMap[$key])) {
        throw "Missing required env var: $key"
    }
}

$catalog = $envMap["TRINO_CATALOG"]
$schema = $envMap["TRINO_SCHEMA"]
$profilesDirPath = (Resolve-Path $DbtProfilesDir).Path

Invoke-Step "render dbt profile" {
    powershell -ExecutionPolicy Bypass -File .\scripts\render_dbt_profile.ps1 -EnvFile $EnvFile
}

Invoke-Step "ensure trino is running" {
    docker compose -f $ComposeFile up -d trino | Out-Host
}

Invoke-Step "check dbt availability from analytics group" {
    Push-Location .\analytics
    try {
        uv run --group analytics dbt --version | Out-Host
    }
    finally {
        Pop-Location
    }
}

Invoke-Step "build staging and mart models" {
    $env:DBT_PROFILES_DIR = $profilesDirPath
    Push-Location .\analytics
    try {
        uv run --group analytics dbt run --select stg_silver_events fct_daily_events fct_daily_revenue fct_daily_conversion
        uv run --group analytics dbt test --select stg_silver_events fct_daily_events fct_daily_revenue fct_daily_conversion
    }
    finally {
        Pop-Location
    }
}

Invoke-Step "verify mart row counts in trino" {
    docker exec -i $TrinoContainer trino --execute "select count(*) as row_count from $catalog.$schema.fct_daily_events" | Out-Host
    docker exec -i $TrinoContainer trino --execute "select count(*) as row_count from $catalog.$schema.fct_daily_revenue" | Out-Host
    docker exec -i $TrinoContainer trino --execute "select count(*) as row_count from $catalog.$schema.fct_daily_conversion" | Out-Host
}

Invoke-Step "verify mart contents in trino" {
    docker exec -i $TrinoContainer trino --execute "select * from $catalog.$schema.fct_daily_events order by event_date" | Out-Host
    docker exec -i $TrinoContainer trino --execute "select * from $catalog.$schema.fct_daily_revenue order by event_date" | Out-Host
    docker exec -i $TrinoContainer trino --execute "select * from $catalog.$schema.fct_daily_conversion order by event_date" | Out-Host
}

Write-Host ""
Write-Host "OK: dbt-trino analytics smoke passed" -ForegroundColor Green