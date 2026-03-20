$script:SparkContainer = "lab-spark"
$script:SparkSubmitPath = "/opt/spark/bin/spark-submit"
$script:IvyRoot = "/tmp/.ivy2"
$script:SparkUserUidGid = "185:185"

$script:IcebergVersion = "1.6.0"
$script:HadoopAwsVersion = "3.3.4"

$script:SparkPackages = @(
  "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:$script:IcebergVersion",
  "org.apache.hadoop:hadoop-aws:$script:HadoopAwsVersion"
) -join ","

function Write-SparkSmokeVersions {
  Write-Host "INFO: Using pinned versions ICEBERG=$script:IcebergVersion, HADOOP_AWS=$script:HadoopAwsVersion"
}

function Initialize-SparkIvyCache {
  $cmd = @(
    "docker", "exec", "-u", "0", "-i", $script:SparkContainer,
    "bash", "-lc",
    "mkdir -p $script:IvyRoot/cache $script:IvyRoot/jars && chown -R $script:SparkUserUidGid $script:IvyRoot && ls -ld $script:IvyRoot $script:IvyRoot/cache $script:IvyRoot/jars"
  )

  Write-Host "INFO: Preparing ivy cache inside container"
  Write-Host ("  " + ($cmd -join " "))

  & $cmd[0] $cmd[1..($cmd.Length-1)] | Out-Host
  return [int]$LASTEXITCODE
}

function Invoke-SparkSubmit {
  param(
    [Parameter(Mandatory = $true)]
    [string[]]$AppArgs
  )

  $baseArgs = @(
    $script:SparkSubmitPath,
    "--conf", "spark.jars.ivy=$script:IvyRoot",
    "--packages", $script:SparkPackages
  )

  $cmd = @("docker", "exec", "-i", $script:SparkContainer) + $baseArgs + $AppArgs

  Write-Host "INFO: Running:"
  Write-Host ("  " + ($cmd -join " "))

  & $cmd[0] $cmd[1..($cmd.Length-1)] | Out-Host
  return [int]$LASTEXITCODE
}