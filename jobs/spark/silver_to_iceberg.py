from __future__ import annotations

import argparse

from pyspark.sql import SparkSession, functions as F


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    p.add_argument("--bucket", default="datalake")
    p.add_argument("--silver_prefix", default="silver/events")
    p.add_argument("--catalog", default="local")
    p.add_argument("--namespace", default="lakehouse")
    p.add_argument("--table", default="silver_events")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    spark = (
        SparkSession.builder.appName("silver_to_iceberg")
        # spark-defaults.conf를 주로 쓰되, 여기서도 안전하게 UTC 고정
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )

    # 입력 Parquet (멀티 파트)
    silver_path = f"s3a://{args.bucket}/{args.silver_prefix}/dt={args.date}/*.parquet"

    df = spark.read.parquet(silver_path)

    # Iceberg 테이블 partitioning을 위해 dt 컬럼 추가
    df = df.withColumn("dt", F.lit(args.date))

    full_table = f"{args.catalog}.{args.namespace}.{args.table}"

    # namespace 생성
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {args.catalog}.{args.namespace}")

    # 테이블이 없다면 생성(스키마는 DF 기반)
    # Iceberg는 overwritePartitions가 가능하므로 rerun 안전성 확보
    (
        df.writeTo(full_table)
        .using("iceberg")
        .tableProperty("format-version", "2")
        .partitionedBy("dt")
        .createOrReplace()
    )

    # dt 파티션만 덮어쓰기(동일 date rerun 안전)
    (df.writeTo(full_table).overwritePartitions())

    # smoke 출력(간단 count)
    cnt = spark.table(full_table).where(F.col("dt") == args.date).count()
    print(f"OK: wrote iceberg table={full_table} dt={args.date} rows={cnt}")

    spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
