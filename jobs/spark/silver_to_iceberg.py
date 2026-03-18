from __future__ import annotations

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructField, StructType


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--bucket", default="datalake")
    parser.add_argument("--silver-prefix", default="silver/events")
    parser.add_argument("--catalog", default="local")
    parser.add_argument("--schema", default="lakehouse")
    parser.add_argument("--table", default="silver_events")
    return parser.parse_args()


def align_df_to_schema(df, target_schema: StructType):
    """
    Align a DataFrame to an existing Iceberg table schema.

    Rules:
    - if a target column is missing in df, add it as NULL cast to target type
    - keep only target columns
    - preserve target column order
    """
    for field in target_schema.fields:
        if field.name not in df.columns:
            df = df.withColumn(field.name, F.lit(None).cast(field.dataType))

    ordered_cols = [F.col(field.name) for field in target_schema.fields]
    return df.select(*ordered_cols)


def main() -> int:
    args = parse_args()

    spark = (
        SparkSession.builder.appName("silver_to_iceberg")
        .getOrCreate()
    )

    silver_path = f"s3a://{args.bucket}/{args.silver_prefix}/dt={args.date}/"
    full_table = f"{args.catalog}.{args.schema}.{args.table}"

    df = spark.read.parquet(silver_path).withColumn("dt", F.lit(args.date))

    if not spark.catalog.tableExists(full_table):
        (
            df.writeTo(full_table)
            .using("iceberg")
            .partitionedBy(F.col("dt"))
            .create()
        )

        row_count = df.count()
        print(f"OK: wrote iceberg table={full_table} dt={args.date} rows={row_count}")
        spark.stop()
        return 0

    target_schema = spark.table(full_table).schema
    aligned_df = align_df_to_schema(df, target_schema)

    (
        aligned_df.writeTo(full_table)
        .overwritePartitions()
    )

    row_count = aligned_df.count()
    print(f"OK: overwrote iceberg table={full_table} dt={args.date} rows={row_count}")
    spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())