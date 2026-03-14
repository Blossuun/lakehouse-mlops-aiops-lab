$ErrorActionPreference = "Stop"

$repoRoot = Split-Path $PSScriptRoot -Parent
$cachePath = Join-Path $repoRoot "infra\hive\cache"
New-Item -ItemType Directory -Force $cachePath | Out-Null

$files = @(
    @{
        Name = "hadoop-aws-3.3.4.jar"
        Url  = "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar"
    },
    @{
        Name = "aws-java-sdk-bundle-1.12.262.jar"
        Url  = "https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar"
    }
)

foreach ($file in $files) {
    $target = Join-Path $cachePath $file.Name
    if (Test-Path $target) {
        Write-Host "Using cached $($file.Name)"
    }
    else {
        Write-Host "Downloading $($file.Name)"
        Invoke-WebRequest -Uri $file.Url -OutFile $target
    }
}

Write-Host "OK: Hive cache is ready"
exit 0