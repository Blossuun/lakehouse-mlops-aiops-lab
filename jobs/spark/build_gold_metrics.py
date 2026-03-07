from __future__ import annotations

import argparse

from pyspark.sql import SparkSession, functions as F


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", default="local")
    p.add_argument("--silver-namespace", default="lakehouse")
    p.add_argument("--silver-table", default="silver_events")
    p.add_argument("--gold-namespace", default="gold")
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    spark = (
        SparkSession.builder.appName("build_gold_metrics")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.catalogImplementation", "in-memory")
        .getOrCreate()
    )

    silver_table = f"{args.catalog}.{args.silver_namespace}.{args.silver_table}"

    df = spark.table(silver_table).where(F.col("dt") == args.date).cache()

    total_count = df.count()
    if total_count == 0:
        print(f"FAIL: no rows found for dt={args.date}")
        return 2

    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {args.catalog}.{args.gold_namespace}")

    # 1) daily_event_metrics
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

    target = f"{args.catalog}.{args.gold_namespace}.daily_event_metrics"

    try:
        (
            event_metrics.writeTo(target)
            .using("iceberg")
            .tableProperty("format-version", "2")
            .partitionedBy("dt")
            .create()
        )
    except Exception:
        pass

    event_metrics.writeTo(target).overwritePartitions()

    # 2) daily_revenue_metrics
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

    revenue_target = f"{args.catalog}.{args.gold_namespace}.daily_revenue_metrics"

    try:
        (
            revenue_metrics.writeTo(revenue_target)
            .using("iceberg")
            .tableProperty("format-version", "2")
            .partitionedBy("dt")
            .create()
        )
    except Exception:
        pass

    revenue_metrics.writeTo(revenue_target).overwritePartitions()

    # 3) daily_conversion_metrics
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
    )

    conversion_target = f"{args.catalog}.{args.gold_namespace}.daily_conversion_metrics"

    try:
        (
            conversion_metrics.writeTo(conversion_target)
            .using("iceberg")
            .tableProperty("format-version", "2")
            .partitionedBy("dt")
            .create()
        )
    except Exception:
        pass

    conversion_metrics.writeTo(conversion_target).overwritePartitions()

    print(f"OK: built gold metrics for dt={args.date}")

    df.unpersist()
    spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
