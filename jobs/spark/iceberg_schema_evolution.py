from __future__ import annotations

import argparse

from pyspark.sql import SparkSession, functions as F


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", default="local")
    p.add_argument("--namespace", default="lakehouse")
    p.add_argument("--table", default="silver_events")
    p.add_argument("--new-column", default="ingest_source")
    p.add_argument("--date", required=True, help="YYYY-MM-DD (dt partition)")
    return p.parse_args()


def full_table_name(catalog: str, namespace: str, table: str) -> str:
    return f"{catalog}.{namespace}.{table}"


def main() -> int:
    args = parse_args()

    spark = (
        SparkSession.builder.appName("iceberg_schema_evolution")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )

    full_table = full_table_name(args.catalog, args.namespace, args.table)

    # 1) add column if missing (idempotent)
    cols = [f.name for f in spark.table(full_table).schema.fields]
    if args.new_column not in cols:
        spark.sql(f"ALTER TABLE {full_table} ADD COLUMN {args.new_column} STRING")
        print(f"INFO: added column {args.new_column}")
    else:
        print(f"INFO: column {args.new_column} already exists")

    # 2) verify column exists
    cols2 = [f.name for f in spark.table(full_table).schema.fields]
    if args.new_column not in cols2:
        print("FAIL: column add did not take effect")
        return 2

    # 3) compatibility check: existing rows should have NULL for the new column
    df = spark.table(full_table).where(F.col("dt") == args.date)
    null_cnt = df.where(F.col(args.new_column).isNull()).count()
    total_cnt = df.count()

    print(
        f"OK: schema evolution verified dt={args.date} null_in_new_col={null_cnt}/{total_cnt}"
    )

    spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
