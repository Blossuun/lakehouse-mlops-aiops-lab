$ErrorActionPreference = "Stop"

$repoRoot = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $repoRoot "infra\.env"

if (!(Test-Path $envFile)) {
    Write-Host "FAIL: infra/.env not found"
    exit 1
}

# load env variables
Get-Content $envFile | ForEach-Object {
    if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
        $name = $matches[1]
        $value = $matches[2]
        Set-Item -Path "Env:$name" -Value $value
    }
}

function Render-Template($template, $output) {

    $content = Get-Content $template -Raw

    $content = $content.Replace('${AWS_ACCESS_KEY_ID}', $env:AWS_ACCESS_KEY_ID)
    $content = $content.Replace('${AWS_SECRET_ACCESS_KEY}', $env:AWS_SECRET_ACCESS_KEY)
    $content = $content.Replace('${AWS_DEFAULT_REGION}', $env:AWS_DEFAULT_REGION)
    $content = $content.Replace('${MINIO_ENDPOINT}', "http://minio:9000")

    Set-Content $output $content
}

$hiveTemplate = Join-Path $repoRoot "infra\hive\conf\core-site.xml.template"
$hiveOutput = Join-Path $repoRoot "infra\hive\conf\core-site.xml"

$trinoTemplate = Join-Path $repoRoot "infra\trino\etc\catalog\iceberg.properties.template"
$trinoOutput = Join-Path $repoRoot "infra\trino\etc\catalog\iceberg.properties"

Render-Template $hiveTemplate $hiveOutput
Render-Template $trinoTemplate $trinoOutput

Write-Host "OK: catalog configuration files rendered"