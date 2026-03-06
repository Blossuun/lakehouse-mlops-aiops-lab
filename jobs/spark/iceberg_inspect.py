from __future__ import annotations

import argparse

from pyspark.sql import SparkSession, functions as F


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", default="local")
    p.add_argument("--namespace", default="lakehouse")
    p.add_argument("--table", default="silver_events")
    p.add_argument("--limit", type=int, default=10)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    spark = (
        SparkSession.builder.appName("iceberg_inspect")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.catalogImplementation", "in-memory")
        .getOrCreate()
    )

    full_table = f"{args.catalog}.{args.namespace}.{args.table}"

    # snapshots
    snaps = spark.table(f"{full_table}.snapshots").select(
        "snapshot_id", "parent_id", "committed_at", "operation", "summary"
    )
    print("=== snapshots (latest) ===")
    snaps.orderBy(F.col("committed_at").desc()).show(args.limit, truncate=False)

    # history
    hist = spark.table(f"{full_table}.history").select(
        "made_current_at", "snapshot_id", "parent_id", "is_current_ancestor"
    )
    print("=== history (latest) ===")
    hist.orderBy(F.col("made_current_at").desc()).show(args.limit, truncate=False)

    spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
