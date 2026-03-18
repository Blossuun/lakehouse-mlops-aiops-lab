from __future__ import annotations

import argparse
import json

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


ALLOWED_EVENT_TYPES = ["view", "search", "add_to_cart", "purchase", "refund"]
ALLOWED_SCHEMA_VERSIONS = [1, 2]
LATE_EVENT_RATIO_THRESHOLD = 0.05


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--bucket", default="datalake")
    parser.add_argument("--catalog", default="local")
    parser.add_argument("--schema", default="lakehouse")
    parser.add_argument("--table", default="silver_events")
    parser.add_argument(
        "--report-out",
        default=None,
        help="Full output URI or directory URI for the JSON report. Kept for backward compatibility.",
    )
    parser.add_argument(
        "--report-prefix",
        default="audit/quality_checks",
        help="Prefix used only when --report-out is not provided.",
    )
    return parser.parse_args()


def normalize_report_uri(args: argparse.Namespace) -> str:
    if args.report_out:
        report_out = args.report_out.rstrip("/")

        if report_out.endswith(".json"):
            return report_out

        return f"{report_out}/report.json"

    return f"s3a://{args.bucket}/{args.report_prefix}/dt={args.date}/report.json"


def write_text_via_hadoop_fs(spark: SparkSession, uri: str, text: str) -> None:
    jvm = spark._jvm
    hconf = spark._jsc.hadoopConfiguration()

    path = jvm.org.apache.hadoop.fs.Path(uri)
    fs = path.getFileSystem(hconf)

    parent = path.getParent()
    if parent is not None and not fs.exists(parent):
        fs.mkdirs(parent)

    if fs.exists(path):
        fs.delete(path, False)

    stream = fs.create(path, True)
    try:
        stream.write(bytearray(text.encode("utf-8")))
    finally:
        stream.close()


def build_rule(
    name: str, passed: bool, failed_rows: int, extra: dict | None = None
) -> dict:
    rule = {
        "name": name,
        "passed": bool(passed),
        "failed_rows": int(failed_rows),
    }
    if extra:
        rule.update(extra)
    return rule


def main() -> int:
    args = parse_args()

    spark = SparkSession.builder.appName("check_silver_quality").getOrCreate()

    full_table = f"{args.catalog}.{args.schema}.{args.table}"

    df = spark.table(full_table).filter(F.col("dt") == args.date).cache()

    metrics_row = df.agg(
        F.count(F.lit(1)).alias("row_count"),
        F.countDistinct("event_id").alias("distinct_event_id_count"),
        F.sum(
            F.when(~F.col("event_type").isin(ALLOWED_EVENT_TYPES), 1).otherwise(0)
        ).alias("invalid_event_type_count"),
        F.sum(
            F.when(~F.col("schema_version").isin(ALLOWED_SCHEMA_VERSIONS), 1).otherwise(
                0
            )
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
        ).alias("late_event_count"),
        F.sum(F.when(F.col("price") < 0, 1).otherwise(0)).alias("negative_price_count"),
        F.sum(F.when(F.col("total_amount") < 0, 1).otherwise(0)).alias(
            "negative_total_amount_count"
        ),
        F.sum(F.when(F.col("refund_amount") < 0, 1).otherwise(0)).alias(
            "negative_refund_amount_count"
        ),
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

    row_count = int(metrics_row["row_count"])
    distinct_event_id_count = int(metrics_row["distinct_event_id_count"])
    duplicate_event_id_count = row_count - distinct_event_id_count
    invalid_event_type_count = int(metrics_row["invalid_event_type_count"] or 0)
    invalid_schema_version_count = int(metrics_row["invalid_schema_version_count"] or 0)
    null_event_time_count = int(metrics_row["null_event_time_count"] or 0)
    null_ingest_time_count = int(metrics_row["null_ingest_time_count"] or 0)
    late_event_count = int(metrics_row["late_event_count"] or 0)
    negative_price_count = int(metrics_row["negative_price_count"] or 0)
    negative_total_amount_count = int(metrics_row["negative_total_amount_count"] or 0)
    negative_refund_amount_count = int(metrics_row["negative_refund_amount_count"] or 0)
    purchase_missing_order_id_count = int(
        metrics_row["purchase_missing_order_id_count"] or 0
    )
    search_missing_query_count = int(metrics_row["search_missing_query_count"] or 0)
    refund_missing_amount_count = int(metrics_row["refund_missing_amount_count"] or 0)

    late_event_ratio = (late_event_count / row_count) if row_count > 0 else 1.0

    rules = [
        build_rule(
            name="partition_not_empty",
            passed=row_count > 0,
            failed_rows=0 if row_count > 0 else 1,
        ),
        build_rule(
            name="event_id_unique",
            passed=duplicate_event_id_count == 0,
            failed_rows=duplicate_event_id_count,
        ),
        build_rule(
            name="event_type_allowed",
            passed=invalid_event_type_count == 0,
            failed_rows=invalid_event_type_count,
            extra={"allowed_values": ALLOWED_EVENT_TYPES},
        ),
        build_rule(
            name="schema_version_allowed",
            passed=invalid_schema_version_count == 0,
            failed_rows=invalid_schema_version_count,
            extra={"allowed_values": ALLOWED_SCHEMA_VERSIONS},
        ),
        build_rule(
            name="event_time_not_null",
            passed=null_event_time_count == 0,
            failed_rows=null_event_time_count,
        ),
        build_rule(
            name="ingest_time_not_null",
            passed=null_ingest_time_count == 0,
            failed_rows=null_ingest_time_count,
        ),
        build_rule(
            name="event_time_lte_ingest_time_ratio",
            passed=late_event_ratio <= LATE_EVENT_RATIO_THRESHOLD,
            failed_rows=late_event_count,
            extra={
                "actual_ratio": late_event_ratio,
                "threshold": LATE_EVENT_RATIO_THRESHOLD,
            },
        ),
        build_rule(
            name="price_non_negative",
            passed=negative_price_count == 0,
            failed_rows=negative_price_count,
        ),
        build_rule(
            name="total_amount_non_negative",
            passed=negative_total_amount_count == 0,
            failed_rows=negative_total_amount_count,
        ),
        build_rule(
            name="refund_amount_non_negative",
            passed=negative_refund_amount_count == 0,
            failed_rows=negative_refund_amount_count,
        ),
        build_rule(
            name="purchase_requires_order_id",
            passed=purchase_missing_order_id_count == 0,
            failed_rows=purchase_missing_order_id_count,
        ),
        build_rule(
            name="search_requires_search_query",
            passed=search_missing_query_count == 0,
            failed_rows=search_missing_query_count,
        ),
        build_rule(
            name="refund_requires_refund_amount",
            passed=refund_missing_amount_count == 0,
            failed_rows=refund_missing_amount_count,
        ),
    ]

    overall_passed = all(rule["passed"] for rule in rules)

    report = {
        "table": full_table,
        "date": args.date,
        "row_count": row_count,
        "overall_passed": overall_passed,
        "rules": rules,
    }

    report_uri = normalize_report_uri(args)
    report_text = json.dumps(report, ensure_ascii=False, indent=2)

    write_text_via_hadoop_fs(spark, report_uri, report_text)

    print(f"OK: quality report uploaded to {report_uri}")

    df.unpersist()
    spark.stop()

    return 0 if overall_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
