from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from pyspark.sql import DataFrame, Row, SparkSession, functions as F


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", default="local")
    p.add_argument("--silver-namespace", default="lakehouse")
    p.add_argument("--silver-table", default="silver_events")
    p.add_argument("--gold-namespace", default="gold")
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    p.add_argument(
        "--mode",
        default="single-pass",
        choices=["single-pass", "with-cache", "multi-pass"],
        help="execution mode for Gold metrics",
    )
    p.add_argument(
        "--metrics-out",
        default=None,
        help=(
            "optional output file path (container-local path, e.g. /tmp/results.csv). "
            "Note: when running via docker exec, this path refers to the container filesystem, "
            "not the host."
        ),
    )
    return p.parse_args()


def write_partitioned_iceberg(
    spark: SparkSession, df: DataFrame, target: str, partition_col: str = "dt"
) -> None:
    created = False

    if not spark.catalog.tableExists(target):
        (
            df.writeTo(target)
            .using("iceberg")
            .tableProperty("format-version", "2")
            .partitionedBy(partition_col)
            .create()
        )
        created = True
        print(f"INFO: created gold table {target}")

    if not created:
        df.writeTo(target).overwritePartitions()


def build_single_pass_base_metrics(df: DataFrame, date: str) -> DataFrame:
    base_metrics_row: Row = (
        df.agg(
            F.count("*").alias("total_events"),
            F.sum(F.when(F.col("event_type") == "view", 1).otherwise(0)).alias(
                "view_events"
            ),
            F.sum(F.when(F.col("event_type") == "search", 1).otherwise(0)).alias(
                "search_events"
            ),
            F.sum(F.when(F.col("event_type") == "add_to_cart", 1).otherwise(0)).alias(
                "add_to_cart_events"
            ),
            F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias(
                "purchase_events"
            ),
            F.sum(F.when(F.col("event_type") == "refund", 1).otherwise(0)).alias(
                "refund_events"
            ),
            F.sum(
                F.when(
                    F.col("event_type") == "purchase", F.col("total_amount")
                ).otherwise(0)
            ).alias("gross_revenue"),
            F.sum(
                F.when(
                    F.col("event_type") == "refund", F.col("refund_amount")
                ).otherwise(0)
            ).alias("refund_amount"),
        )
        .withColumn("dt", F.lit(date))
        .select(
            "dt",
            "total_events",
            "view_events",
            "search_events",
            "add_to_cart_events",
            "purchase_events",
            "refund_events",
            "gross_revenue",
            "refund_amount",
        )
        .collect()[0]
    )
    return df.sparkSession.createDataFrame([base_metrics_row.asDict()])


def build_multi_pass_metrics(df: DataFrame) -> tuple[DataFrame, DataFrame, DataFrame]:
    event_metrics = df.groupBy("dt").agg(
        F.count("*").alias("total_events"),
        F.sum(F.when(F.col("event_type") == "view", 1).otherwise(0)).alias(
            "view_events"
        ),
        F.sum(F.when(F.col("event_type") == "search", 1).otherwise(0)).alias(
            "search_events"
        ),
        F.sum(F.when(F.col("event_type") == "add_to_cart", 1).otherwise(0)).alias(
            "add_to_cart_events"
        ),
        F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias(
            "purchase_events"
        ),
        F.sum(F.when(F.col("event_type") == "refund", 1).otherwise(0)).alias(
            "refund_events"
        ),
    )

    revenue_metrics = (
        df.groupBy("dt")
        .agg(
            F.sum(
                F.when(
                    F.col("event_type") == "purchase", F.col("total_amount")
                ).otherwise(0)
            ).alias("gross_revenue"),
            F.sum(
                F.when(
                    F.col("event_type") == "refund", F.col("refund_amount")
                ).otherwise(0)
            ).alias("refund_amount"),
        )
        .withColumn("net_revenue", F.col("gross_revenue") - F.col("refund_amount"))
    )

    conversion_base = df.groupBy("dt").agg(
        F.sum(F.when(F.col("event_type") == "view", 1).otherwise(0)).alias(
            "view_events"
        ),
        F.sum(F.when(F.col("event_type") == "add_to_cart", 1).otherwise(0)).alias(
            "add_to_cart_events"
        ),
        F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias(
            "purchase_events"
        ),
    )

    conversion_metrics = (
        conversion_base.withColumn(
            "view_to_cart_rate",
            F.when(
                F.col("view_events") > 0,
                F.col("add_to_cart_events") / F.col("view_events"),
            ).otherwise(F.lit(None)),
        )
        .withColumn(
            "cart_to_purchase_rate",
            F.when(
                F.col("add_to_cart_events") > 0,
                F.col("purchase_events") / F.col("add_to_cart_events"),
            ).otherwise(F.lit(None)),
        )
        .withColumn(
            "view_to_purchase_rate",
            F.when(
                F.col("view_events") > 0,
                F.col("purchase_events") / F.col("view_events"),
            ).otherwise(F.lit(None)),
        )
        .select(
            "dt",
            "view_events",
            "add_to_cart_events",
            "purchase_events",
            "view_to_cart_rate",
            "cart_to_purchase_rate",
            "view_to_purchase_rate",
        )
    )

    return event_metrics, revenue_metrics, conversion_metrics


def build_single_pass_metrics(
    base_metrics: DataFrame,
) -> tuple[DataFrame, DataFrame, DataFrame]:
    event_metrics = base_metrics.select(
        "dt",
        "total_events",
        "view_events",
        "search_events",
        "add_to_cart_events",
        "purchase_events",
        "refund_events",
    )

    revenue_metrics = base_metrics.withColumn(
        "net_revenue", F.col("gross_revenue") - F.col("refund_amount")
    ).select("dt", "gross_revenue", "refund_amount", "net_revenue")

    conversion_metrics = (
        base_metrics.withColumn(
            "view_to_cart_rate",
            F.when(
                F.col("view_events") > 0,
                F.col("add_to_cart_events") / F.col("view_events"),
            ).otherwise(F.lit(None)),
        )
        .withColumn(
            "cart_to_purchase_rate",
            F.when(
                F.col("add_to_cart_events") > 0,
                F.col("purchase_events") / F.col("add_to_cart_events"),
            ).otherwise(F.lit(None)),
        )
        .withColumn(
            "view_to_purchase_rate",
            F.when(
                F.col("view_events") > 0,
                F.col("purchase_events") / F.col("view_events"),
            ).otherwise(F.lit(None)),
        )
        .select(
            "dt",
            "view_events",
            "add_to_cart_events",
            "purchase_events",
            "view_to_cart_rate",
            "cart_to_purchase_rate",
            "view_to_purchase_rate",
        )
    )

    return event_metrics, revenue_metrics, conversion_metrics


def append_metrics_line(
    metrics_out: str,
    mode: str,
    date: str,
    elapsed_sec: float,
    total_count: int,
) -> None:
    path = Path(metrics_out)
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()

    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["mode", "date", "elapsed_sec", "total_count"])
        writer.writerow([mode, date, f"{elapsed_sec:.2f}", total_count])


def main() -> int:
    args = parse_args()
    start = time.time()

    spark = (
        SparkSession.builder.appName("build_gold_metrics")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.catalogImplementation", "in-memory")
        .getOrCreate()
    )

    silver_table = f"{args.catalog}.{args.silver_namespace}.{args.silver_table}"

    # NOTE:
    # - single-pass: materialize one aggregated row and derive all outputs from it
    # - with-cache: keep the previous cache-based local reuse strategy for comparison
    # - multi-pass: no cache, repeated scans for comparison baseline
    df = spark.table(silver_table).where(F.col("dt") == args.date)

    if args.mode == "with-cache":
        df = df.cache()

    total_count = df.count()
    if total_count == 0:
        print(f"FAIL: no rows found for dt={args.date}")
        spark.stop()
        return 2

    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {args.catalog}.{args.gold_namespace}")

    if args.mode == "single-pass":
        base_metrics = build_single_pass_base_metrics(df, args.date)
        event_metrics, revenue_metrics, conversion_metrics = build_single_pass_metrics(
            base_metrics
        )
    else:
        event_metrics, revenue_metrics, conversion_metrics = build_multi_pass_metrics(
            df
        )

    event_target = f"{args.catalog}.{args.gold_namespace}.daily_event_metrics"
    revenue_target = f"{args.catalog}.{args.gold_namespace}.daily_revenue_metrics"
    conversion_target = f"{args.catalog}.{args.gold_namespace}.daily_conversion_metrics"

    write_partitioned_iceberg(spark, event_metrics, event_target)
    write_partitioned_iceberg(spark, revenue_metrics, revenue_target)
    write_partitioned_iceberg(spark, conversion_metrics, conversion_target)

    if args.mode == "with-cache":
        df.unpersist()

    elapsed = time.time() - start
    print(f"INFO: execution_time_sec={elapsed:.2f}, mode={args.mode}")

    if args.metrics_out:
        append_metrics_line(
            args.metrics_out, args.mode, args.date, elapsed, total_count
        )

    print(f"OK: built gold metrics for dt={args.date} mode={args.mode}")

    spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
