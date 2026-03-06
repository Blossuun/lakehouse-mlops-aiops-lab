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


def main() -> int:
    args = parse_args()

    spark = (
        SparkSession.builder.appName("check_silver_quality")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.catalogImplementation", "in-memory")
        .getOrCreate()
    )

    full_table = f"{args.catalog}.{args.namespace}.{args.table}"
    df = spark.table(full_table).where(F.col("dt") == args.date).cache()

    total_count = df.count()

    rules: list[dict] = []

    # Rule 1
    rules.append(
        make_rule(
            "partition_not_empty",
            total_count > 0,
            total_count,
            "> 0",
        )
    )

    # total_count == 0이면 나머지 계산은 의미가 약하므로 계속 계산은 하되 fail 유지
    distinct_event_id = df.select("event_id").distinct().count()
    duplicate_count = total_count - distinct_event_id

    rules.append(
        make_rule(
            "event_id_unique",
            duplicate_count == 0,
            duplicate_count,
            0,
        )
    )

    allowed_event_types = ["view", "search", "add_to_cart", "purchase", "refund"]
    invalid_event_type_count = df.where(
        ~F.col("event_type").isin(allowed_event_types) | F.col("event_type").isNull()
    ).count()
    rules.append(
        make_rule(
            "event_type_allowed",
            invalid_event_type_count == 0,
            invalid_event_type_count,
            0,
        )
    )

    invalid_schema_version_count = df.where(
        ~F.col("schema_version").isin([1, 2]) | F.col("schema_version").isNull()
    ).count()
    rules.append(
        make_rule(
            "schema_version_allowed",
            invalid_schema_version_count == 0,
            invalid_schema_version_count,
            0,
        )
    )

    null_event_time_count = df.where(F.col("event_time").isNull()).count()
    rules.append(
        make_rule(
            "event_time_not_null",
            null_event_time_count == 0,
            null_event_time_count,
            0,
        )
    )

    null_ingest_time_count = df.where(F.col("ingest_time").isNull()).count()
    rules.append(
        make_rule(
            "ingest_time_not_null",
            null_ingest_time_count == 0,
            null_ingest_time_count,
            0,
        )
    )

    invalid_time_order_count = df.where(
        F.col("event_time").isNotNull()
        & F.col("ingest_time").isNotNull()
        & (F.col("event_time") > F.col("ingest_time"))
    ).count()
    invalid_time_order_ratio = (
        (invalid_time_order_count / total_count) if total_count > 0 else 1.0
    )
    rules.append(
        make_rule(
            "event_time_lte_ingest_time_ratio",
            invalid_time_order_ratio <= 0.05,
            invalid_time_order_ratio,
            "<= 0.05",
        )
    )

    negative_price_count = df.where(
        F.col("price").isNotNull() & (F.col("price") < 0)
    ).count()
    negative_total_amount_count = df.where(
        F.col("total_amount").isNotNull() & (F.col("total_amount") < 0)
    ).count()
    negative_refund_amount_count = df.where(
        F.col("refund_amount").isNotNull() & (F.col("refund_amount") < 0)
    ).count()

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

    purchase_missing_order_id_count = df.where(
        (F.col("event_type") == "purchase") & F.col("order_id").isNull()
    ).count()
    rules.append(
        make_rule(
            "purchase_requires_order_id",
            purchase_missing_order_id_count == 0,
            purchase_missing_order_id_count,
            0,
        )
    )

    search_missing_query_count = df.where(
        (F.col("event_type") == "search") & F.col("search_query").isNull()
    ).count()
    rules.append(
        make_rule(
            "search_requires_query",
            search_missing_query_count == 0,
            search_missing_query_count,
            0,
        )
    )

    refund_missing_amount_count = df.where(
        (F.col("event_type") == "refund") & F.col("refund_amount").isNull()
    ).count()
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
        # Write a Spark output directory/prefix containing text part files
        spark.createDataFrame([(report_json,)], ["json"]).coalesce(1).write.mode(
            "overwrite"
        ).text(args.report_out)

    df.unpersist()
    spark.stop()
    return 0 if all_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
