from __future__ import annotations

import argparse

from pyspark.sql import DataFrame, Row, SparkSession, functions as F


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", default="local")
    p.add_argument("--silver-namespace", default="lakehouse")
    p.add_argument("--silver-table", default="silver_events")
    p.add_argument("--gold-namespace", default="gold")
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
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


def main() -> int:
    args = parse_args()

    spark = (
        SparkSession.builder.appName("build_gold_metrics")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.catalogImplementation", "in-memory")
        .getOrCreate()
    )

    silver_table = f"{args.catalog}.{args.silver_namespace}.{args.silver_table}"

    # NOTE:
    # We intentionally avoid df.cache() for local Docker/WSL stability.
    # We also avoid repeated scans by materializing a single aggregated row once,
    # then deriving the three Gold tables from that 1-row result.
    df = spark.table(silver_table).where(F.col("dt") == args.date)

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
        .withColumn("dt", F.lit(args.date))
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

    total_count = int(base_metrics_row["total_events"])
    if total_count == 0:
        print(f"FAIL: no rows found for dt={args.date}")
        spark.stop()
        return 2

    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {args.catalog}.{args.gold_namespace}")

    base_metrics = spark.createDataFrame([base_metrics_row.asDict()])

    event_metrics = base_metrics.select(
        "dt",
        "total_events",
        "view_events",
        "search_events",
        "add_to_cart_events",
        "purchase_events",
        "refund_events",
    )

    event_target = f"{args.catalog}.{args.gold_namespace}.daily_event_metrics"
    write_partitioned_iceberg(spark, event_metrics, event_target)

    revenue_metrics = base_metrics.withColumn(
        "net_revenue", F.col("gross_revenue") - F.col("refund_amount")
    ).select("dt", "gross_revenue", "refund_amount", "net_revenue")

    revenue_target = f"{args.catalog}.{args.gold_namespace}.daily_revenue_metrics"
    write_partitioned_iceberg(spark, revenue_metrics, revenue_target)

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

    conversion_target = f"{args.catalog}.{args.gold_namespace}.daily_conversion_metrics"
    write_partitioned_iceberg(spark, conversion_metrics, conversion_target)

    print(f"OK: built gold metrics for dt={args.date}")

    spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
