param(
    [string]$EnvFile = ".\infra\.env",
    [string]$TemplateFile = ".\analytics\profiles\profiles.yml.template",
    [string]$OutputFile = ".\analytics\profiles\profiles.yml"
)

$ErrorActionPreference = "Stop"

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

if (-not (Test-Path $TemplateFile)) {
    throw "Template file not found: $TemplateFile"
}

$vars = Read-DotEnv -Path $EnvFile
$template = Get-Content $TemplateFile -Raw

$requiredKeys = @(
    "TRINO_HOST",
    "TRINO_PORT",
    "TRINO_USER",
    "TRINO_CATALOG",
    "TRINO_SCHEMA"
)

foreach ($key in $requiredKeys) {
    if (-not $vars.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($vars[$key])) {
        throw "Missing required env var: $key"
    }

    $placeholder = '${' + $key + '}'
    $template = $template.Replace($placeholder, $vars[$key])
}

$parentDir = Split-Path -Parent $OutputFile
if (-not (Test-Path $parentDir)) {
    New-Item -ItemType Directory -Force -Path $parentDir | Out-Null
}

Set-Content -Path $OutputFile -Value $template -Encoding UTF8

Write-Host "OK: rendered dbt profile -> $OutputFile"