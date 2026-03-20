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


def align_df_to_table_schema(df, target_df):
    """
    Align incoming DF to an existing Iceberg table schema.

    Strategy:
    - add missing target columns as NULL with the correct Spark type
    - reorder/select columns to match the target schema exactly

    This keeps overwritePartitions() rerunnable even after schema evolution.
    """
    target_schema = target_df.schema
    source_cols = set(df.columns)

    for field in target_schema.fields:
        if field.name not in source_cols:
            df = df.withColumn(field.name, F.lit(None).cast(field.dataType))

    ordered_cols = [
        F.col(field.name).cast(field.dataType).alias(field.name)
        for field in target_schema.fields
    ]
    return df.select(*ordered_cols)


def main() -> int:
    args = parse_args()

    spark = (
        SparkSession.builder.appName("silver_to_iceberg")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )

    silver_path = f"s3a://{args.bucket}/{args.silver_prefix}/dt={args.date}/*.parquet"
    df = spark.read.parquet(silver_path)

    # partition column for Iceberg
    df = df.withColumn("dt", F.lit(args.date))

    full_table = f"{args.catalog}.{args.namespace}.{args.table}"

    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {args.catalog}.{args.namespace}")

    created = False

    # create table first if missing
    if not spark.catalog.tableExists(full_table):
        (
            df.writeTo(full_table)
            .using("iceberg")
            .tableProperty("format-version", "2")
            .partitionedBy("dt")
            .create()
        )
        created = True
        print(f"INFO: created iceberg table {full_table}")

    # only overwrite when the table already existed
    if not created:
        target_df = spark.table(full_table)
        df = align_df_to_table_schema(df, target_df)

        # rerun-safe partition overwrite
        df.writeTo(full_table).overwritePartitions()

    cnt = spark.table(full_table).where(F.col("dt") == args.date).count()
    print(f"OK: wrote iceberg table={full_table} dt={args.date} rows={cnt}")

    spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
