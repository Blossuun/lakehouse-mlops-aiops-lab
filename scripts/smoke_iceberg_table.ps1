param(
  [string]$Date = "2026-02-27"
)

# Start infra if needed (user runs separately)

# Run spark-submit inside the spark container with pinned packages
# NOTE: Adjust versions if Spark Hadoop version mismatch occurs.
$ICEBERG_VERSION = "1.6.0"
$HADOOP_AWS_VERSION = "3.3.4"
$AWS_SDK_BUNDLE_VERSION = "1.12.262"

$PACKAGES = @(
  "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:$ICEBERG_VERSION",
  "org.apache.hadoop:hadoop-aws:$HADOOP_AWS_VERSION"
) -join ","

docker exec -it lab-spark /opt/spark/bin/spark-submit `
  --conf spark.jars.ivy=/tmp/.ivy2 `
  --packages $PACKAGES `
  /opt/lab/jobs/spark/silver_to_iceberg.py `
  --date $Date

if ($LASTEXITCODE -ne 0) {
  Write-Host "FAIL: spark-submit failed"
  exit 2
}

Write-Host "OK: smoke_iceberg_table completed"