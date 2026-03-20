from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from pyspark.sql import SparkSession, functions as F


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", default="local")
    p.add_argument("--namespace", default="lakehouse")
    p.add_argument("--table", default="silver_events")
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    p.add_argument("--report-out", default=None, help="s3a path to write JSON report")
    return p.parse_args()


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def make_rule(
    name: str, passed: bool, actual, expected, severity: str = "FAIL"
) -> dict:
    return {
        "rule": name,
        "passed": bool(passed),
        "actual": actual,
        "expected": expected,
        "severity": severity,
    }


def scalar_int(value) -> int:
    if value is None:
        return 0
    return int(value)


def scalar_float(value) -> float:
    if value is None:
        return 0.0
    return float(value)


def main() -> int:
    args = parse_args()

    spark = (
        SparkSession.builder.appName("check_silver_quality")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.catalogImplementation", "in-memory")
        .getOrCreate()
    )

    full_table = f"{args.catalog}.{args.namespace}.{args.table}"
    df = spark.table(full_table).where(F.col("dt") == args.date)

    allowed_event_types = ["view", "search", "add_to_cart", "purchase", "refund"]

    metrics_row = df.agg(
        F.count(F.lit(1)).alias("total_count"),
        F.count("event_id").alias("non_null_event_id_count"),
        F.countDistinct("event_id").alias("distinct_non_null_event_id_count"),
        F.sum(F.when(F.col("event_id").isNull(), 1).otherwise(0)).alias(
            "null_event_id_count"
        ),
        F.sum(
            F.when(
                (~F.col("event_type").isin(allowed_event_types))
                | F.col("event_type").isNull(),
                1,
            ).otherwise(0)
        ).alias("invalid_event_type_count"),
        F.sum(
            F.when(
                (~F.col("schema_version").isin([1, 2]))
                | F.col("schema_version").isNull(),
                1,
            ).otherwise(0)
        ).alias("invalid_schema_version_count"),
        F.sum(F.when(F.col("event_time").isNull(), 1).otherwise(0)).alias(
            "null_event_time_count"
        ),
        F.sum(F.when(F.col("ingest_time").isNull(), 1).otherwise(0)).alias(
            "null_ingest_time_count"
        ),
        F.sum(
            F.when(
                F.col("event_time").isNotNull()
                & F.col("ingest_time").isNotNull()
                & (F.col("event_time") > F.col("ingest_time")),
                1,
            ).otherwise(0)
        ).alias("invalid_time_order_count"),
        F.sum(
            F.when(
                F.col("price").isNotNull() & (F.col("price") < 0),
                1,
            ).otherwise(0)
        ).alias("negative_price_count"),
        F.sum(
            F.when(
                F.col("total_amount").isNotNull() & (F.col("total_amount") < 0),
                1,
            ).otherwise(0)
        ).alias("negative_total_amount_count"),
        F.sum(
            F.when(
                F.col("refund_amount").isNotNull() & (F.col("refund_amount") < 0),
                1,
            ).otherwise(0)
        ).alias("negative_refund_amount_count"),
        F.sum(
            F.when(
                (F.col("event_type") == "purchase") & F.col("order_id").isNull(),
                1,
            ).otherwise(0)
        ).alias("purchase_missing_order_id_count"),
        F.sum(
            F.when(
                (F.col("event_type") == "search") & F.col("search_query").isNull(),
                1,
            ).otherwise(0)
        ).alias("search_missing_query_count"),
        F.sum(
            F.when(
                (F.col("event_type") == "refund") & F.col("refund_amount").isNull(),
                1,
            ).otherwise(0)
        ).alias("refund_missing_amount_count"),
    ).collect()[0]

    total_count = scalar_int(metrics_row["total_count"])
    non_null_event_id_count = scalar_int(metrics_row["non_null_event_id_count"])
    distinct_non_null_event_id_count = scalar_int(
        metrics_row["distinct_non_null_event_id_count"]
    )
    null_event_id_count = scalar_int(metrics_row["null_event_id_count"])

    # Preserve previous semantics:
    # df.select("event_id").distinct().count() counted one null value as one distinct value.
    effective_distinct_event_id_count = distinct_non_null_event_id_count + (
        1 if null_event_id_count > 0 else 0
    )
    duplicate_count = total_count - effective_distinct_event_id_count

    invalid_event_type_count = scalar_int(metrics_row["invalid_event_type_count"])
    invalid_schema_version_count = scalar_int(
        metrics_row["invalid_schema_version_count"]
    )
    null_event_time_count = scalar_int(metrics_row["null_event_time_count"])
    null_ingest_time_count = scalar_int(metrics_row["null_ingest_time_count"])
    invalid_time_order_count = scalar_int(metrics_row["invalid_time_order_count"])
    negative_price_count = scalar_int(metrics_row["negative_price_count"])
    negative_total_amount_count = scalar_int(metrics_row["negative_total_amount_count"])
    negative_refund_amount_count = scalar_int(
        metrics_row["negative_refund_amount_count"]
    )
    purchase_missing_order_id_count = scalar_int(
        metrics_row["purchase_missing_order_id_count"]
    )
    search_missing_query_count = scalar_int(metrics_row["search_missing_query_count"])
    refund_missing_amount_count = scalar_int(metrics_row["refund_missing_amount_count"])

    invalid_time_order_ratio = (
        scalar_float(invalid_time_order_count / total_count) if total_count > 0 else 1.0
    )

    rules: list[dict] = []

    rules.append(
        make_rule(
            "partition_not_empty",
            total_count > 0,
            total_count,
            "> 0",
        )
    )

    rules.append(
        make_rule(
            "event_id_unique",
            duplicate_count == 0,
            duplicate_count,
            0,
        )
    )

    rules.append(
        make_rule(
            "event_type_allowed",
            invalid_event_type_count == 0,
            invalid_event_type_count,
            0,
        )
    )

    rules.append(
        make_rule(
            "schema_version_allowed",
            invalid_schema_version_count == 0,
            invalid_schema_version_count,
            0,
        )
    )

    rules.append(
        make_rule(
            "event_time_not_null",
            null_event_time_count == 0,
            null_event_time_count,
            0,
        )
    )

    rules.append(
        make_rule(
            "ingest_time_not_null",
            null_ingest_time_count == 0,
            null_ingest_time_count,
            0,
        )
    )

    rules.append(
        make_rule(
            "event_time_lte_ingest_time_ratio",
            invalid_time_order_ratio <= 0.05,
            invalid_time_order_ratio,
            "<= 0.05",
        )
    )

    rules.append(
        make_rule(
            "price_non_negative",
            negative_price_count == 0,
            negative_price_count,
            0,
        )
    )

    rules.append(
        make_rule(
            "total_amount_non_negative",
            negative_total_amount_count == 0,
            negative_total_amount_count,
            0,
        )
    )

    rules.append(
        make_rule(
            "refund_amount_non_negative",
            negative_refund_amount_count == 0,
            negative_refund_amount_count,
            0,
        )
    )

    rules.append(
        make_rule(
            "purchase_requires_order_id",
            purchase_missing_order_id_count == 0,
            purchase_missing_order_id_count,
            0,
        )
    )

    rules.append(
        make_rule(
            "search_requires_query",
            search_missing_query_count == 0,
            search_missing_query_count,
            0,
        )
    )

    rules.append(
        make_rule(
            "refund_requires_amount",
            refund_missing_amount_count == 0,
            refund_missing_amount_count,
            0,
        )
    )

    all_passed = all(r["passed"] for r in rules)

    report = {
        "table": full_table,
        "date": args.date,
        "checked_at": utc_now_iso(),
        "row_count": total_count,
        "all_passed": all_passed,
        "rules": rules,
    }

    report_json = json.dumps(report, ensure_ascii=False, indent=2)
    print(report_json)

    if args.report_out:
        spark.createDataFrame([(report_json,)], ["json"]).coalesce(1).write.mode(
            "overwrite"
        ).text(args.report_out)

    spark.stop()
    return 0 if all_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
