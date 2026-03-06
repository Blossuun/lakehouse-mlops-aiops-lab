from __future__ import annotations

import argparse
from typing import Optional

from pyspark.sql import SparkSession, functions as F


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", default="local")
    p.add_argument("--namespace", default="lakehouse")
    p.add_argument("--table", default="silver_events")
    p.add_argument("--date", required=True, help="YYYY-MM-DD (dt partition)")
    return p.parse_args()


def full_table_name(catalog: str, namespace: str, table: str) -> str:
    return f"{catalog}.{namespace}.{table}"


def get_latest_two_snapshot_ids(
    spark: SparkSession, full_table: str
) -> tuple[Optional[int], Optional[int]]:
    snaps = spark.table(f"{full_table}.snapshots").select("snapshot_id", "committed_at")
    rows = snaps.orderBy(F.col("committed_at").desc()).limit(2).collect()
    if not rows:
        return None, None
    latest = int(rows[0]["snapshot_id"])
    prev = int(rows[1]["snapshot_id"]) if len(rows) > 1 else None
    return latest, prev


def read_as_of_snapshot(spark: SparkSession, full_table: str, snapshot_id: int):
    return (
        spark.read.format("iceberg")
        .option("snapshot-id", str(snapshot_id))
        .load(full_table)
    )


def main() -> int:
    args = parse_args()

    spark = (
        SparkSession.builder.appName("iceberg_time_travel")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )

    full_table = full_table_name(args.catalog, args.namespace, args.table)

    latest, prev = get_latest_two_snapshot_ids(spark, full_table)
    if latest is None:
        print("FAIL: no snapshots found")
        return 2
    if prev is None:
        print("FAIL: only 1 snapshot exists; run a rerun/overwrite first")
        return 3

    # current count for dt
    current_cnt = spark.table(full_table).where(F.col("dt") == args.date).count()

    # time travel count for dt (previous snapshot)
    prev_cnt = (
        read_as_of_snapshot(spark, full_table, prev)
        .where(F.col("dt") == args.date)
        .count()
    )

    print(
        f"OK: time travel counts dt={args.date} current={current_cnt} previous_snapshot={prev_cnt} (prev_snapshot_id={prev})"
    )

    spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
