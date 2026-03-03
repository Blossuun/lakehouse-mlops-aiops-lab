from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from lakehouse_mlops_aiops_lab.utils.s3util import (
    S3Config,
    ensure_bucket,
    iter_lines,
    list_keys,
    make_s3_client,
    put_bytes,
    delete_parquet_under_prefix,
)


def parse_iso_utc(s: Any) -> datetime | None:
    """Parse ISO8601 with Z to timezone-aware UTC datetime."""
    if not isinstance(s, str) or not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None or dt.utcoffset() is None:
            return None
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def to_int(v: Any) -> int | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return int(float(s))
        except Exception:
            return None
    return None


def to_str(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        return str(v)
    return None


def get_nested(obj: dict[str, Any], *keys: str) -> Any:
    cur: Any = obj
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


SILVER_SCHEMA = pa.schema(
    [
        pa.field("event_id", pa.string(), nullable=False),
        pa.field("schema_version", pa.int32(), nullable=True),
        pa.field("event_type", pa.string(), nullable=True),
        pa.field("event_time", pa.timestamp("ms", tz="UTC"), nullable=True),
        pa.field("ingest_time", pa.timestamp("ms", tz="UTC"), nullable=True),
        pa.field("user_id", pa.string(), nullable=True),
        pa.field("session_id", pa.string(), nullable=True),
        pa.field("device_os", pa.string(), nullable=True),
        pa.field("device_os_version", pa.string(), nullable=True),
        pa.field("device_app_version", pa.string(), nullable=True),
        pa.field("geo_country", pa.string(), nullable=True),
        pa.field("geo_region", pa.string(), nullable=True),
        pa.field("geo_city", pa.string(), nullable=True),
        pa.field("source_referrer", pa.string(), nullable=True),
        pa.field("source_utm_campaign", pa.string(), nullable=True),
        pa.field("source_utm_medium", pa.string(), nullable=True),
        pa.field("product_id", pa.string(), nullable=True),
        pa.field("category_id", pa.string(), nullable=True),
        pa.field("brand", pa.string(), nullable=True),
        pa.field("price", pa.int64(), nullable=True),
        pa.field("quantity", pa.int32(), nullable=True),
        pa.field("order_id", pa.string(), nullable=True),
        pa.field("total_amount", pa.int64(), nullable=True),
        pa.field("payment_method", pa.string(), nullable=True),
        pa.field("coupon_id", pa.string(), nullable=True),
        pa.field("search_query", pa.string(), nullable=True),
        pa.field("results_count", pa.int32(), nullable=True),
        pa.field("refund_amount", pa.int64(), nullable=True),
        pa.field("reason_code", pa.string(), nullable=True),
        pa.field("payload_json", pa.string(), nullable=True),
    ]
)


def extract_silver_row(raw: dict[str, Any]) -> dict[str, Any] | None:
    event_id = raw.get("event_id")
    if not isinstance(event_id, str) or not event_id:
        return None

    payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else None

    row: dict[str, Any] = {
        "event_id": event_id,
        "schema_version": to_int(raw.get("schema_version")),
        "event_type": to_str(raw.get("event_type")),
        "event_time": parse_iso_utc(raw.get("event_time")),
        "ingest_time": parse_iso_utc(raw.get("ingest_time")),
        "user_id": to_str(raw.get("user_id")),
        "session_id": to_str(raw.get("session_id")),
        "device_os": to_str(get_nested(raw, "device", "os")),
        "device_os_version": to_str(get_nested(raw, "device", "os_version")),
        "device_app_version": to_str(get_nested(raw, "device", "app_version")),
        "geo_country": to_str(get_nested(raw, "geo", "country")),
        "geo_region": to_str(get_nested(raw, "geo", "region")),
        "geo_city": to_str(get_nested(raw, "geo", "city")),
        "source_referrer": to_str(get_nested(raw, "source", "referrer")),
        "source_utm_campaign": to_str(get_nested(raw, "source", "utm_campaign")),
        "source_utm_medium": to_str(get_nested(raw, "source", "utm_medium")),
        "product_id": to_str(payload.get("product_id")) if payload else None,
        "category_id": to_str(payload.get("category_id")) if payload else None,
        "brand": to_str(payload.get("brand")) if payload else None,
        "price": to_int(payload.get("price")) if payload else None,
        "quantity": to_int(payload.get("quantity")) if payload else None,
        "order_id": to_str(payload.get("order_id")) if payload else None,
        "total_amount": to_int(payload.get("total_amount")) if payload else None,
        "payment_method": to_str(payload.get("payment_method")) if payload else None,
        "coupon_id": to_str(payload.get("coupon_id")) if payload else None,
        "search_query": to_str(payload.get("query")) if payload else None,
        "results_count": to_int(payload.get("results_count")) if payload else None,
        "refund_amount": to_int(payload.get("refund_amount")) if payload else None,
        "reason_code": to_str(payload.get("reason_code")) if payload else None,
        "payload_json": json.dumps(payload, ensure_ascii=False) if payload else None,
    }

    # int32 fields normalize
    if row["quantity"] is not None:
        row["quantity"] = int(row["quantity"])
    if row["results_count"] is not None:
        row["results_count"] = int(row["results_count"])

    return row


def rows_to_table(rows: list[dict[str, Any]]) -> pa.Table:
    arrays = []
    for field in SILVER_SCHEMA:
        name = field.name
        arrays.append(pa.array([r.get(name) for r in rows], type=field.type))
    return pa.Table.from_arrays(arrays, schema=SILVER_SCHEMA)


def table_to_parquet_bytes(table: pa.Table) -> bytes:
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, compression="snappy")
    return sink.getvalue().to_pybytes()


def parse_args():
    p = argparse.ArgumentParser(
        description="Transform raw JSONL events in S3 to silver Parquet (chunked)."
    )
    p.add_argument("--date", required=True, help="partition date YYYY-MM-DD (UTC)")
    p.add_argument("--bucket", default="datalake")
    p.add_argument("--raw-prefix", default="raw/events")
    p.add_argument("--silver-prefix", default="silver/events")
    p.add_argument("--row-batch-size", type=int, default=50000)
    p.add_argument("--part-prefix", default="part-")
    p.add_argument("--part-width", type=int, default=5)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    cfg = S3Config.from_env()
    s3 = make_s3_client(cfg)

    # fail fast
    try:
        s3.list_buckets()
    except Exception as exc:
        print(
            "ERROR: Cannot connect to S3 endpoint. Is Docker (MinIO) running? "
            f"Details: {exc}"
        )
        return 2

    ensure_bucket(s3, args.bucket)

    raw_partition_prefix = f"{args.raw_prefix}/dt={args.date}/"
    raw_keys = sorted(
        k
        for k in list_keys(s3, args.bucket, raw_partition_prefix)
        if k.endswith(".jsonl")
    )
    if not raw_keys:
        print(
            f"ERROR: no raw jsonl found under s3://{args.bucket}/{raw_partition_prefix}"
        )
        return 3

    # streaming transform
    seen: set[str] = set()
    batch: list[dict[str, Any]] = []
    total_in = 0
    total_out = 0
    dedup_skipped = 0
    part_idx = 0
    json_parse_errors = 0

    silver_partition_prefix = f"{args.silver_prefix}/dt={args.date}/"

    deleted = delete_parquet_under_prefix(s3, args.bucket, silver_partition_prefix)
    if deleted > 0:
        print(
            f"INFO: deleted {deleted} stale parquet part(s) under s3://{args.bucket}/{silver_partition_prefix}"
        )

    def flush_batch() -> None:
        nonlocal part_idx, total_out, batch
        if not batch:
            return
        table = rows_to_table(batch)
        data = table_to_parquet_bytes(table)
        part_name = f"{args.part_prefix}{part_idx:0{args.part_width}d}.parquet"
        out_key = f"{silver_partition_prefix}{part_name}"
        put_bytes(
            s3, args.bucket, out_key, data, content_type="application/octet-stream"
        )
        total_out += table.num_rows
        part_idx += 1
        batch = []

    for key in raw_keys:
        for line_bytes in iter_lines(s3, args.bucket, key):
            if not line_bytes:
                continue
            try:
                obj = json.loads(line_bytes.decode("utf-8"))
            except Exception:
                json_parse_errors += 1
                continue
            if not isinstance(obj, dict):
                continue

            total_in += 1
            row = extract_silver_row(obj)
            if row is None:
                continue

            eid = row["event_id"]
            if eid in seen:
                dedup_skipped += 1
                continue
            seen.add(eid)

            batch.append(row)
            if len(batch) >= args.row_batch_size:
                flush_batch()

    flush_batch()

    print(
        "OK: wrote silver parquet "
        f"s3://{args.bucket}/{silver_partition_prefix} "
        f"parts={part_idx} rows={total_out} (raw_lines={total_in}, "
        f"dedup_skipped={dedup_skipped}, json_parse_errors={json_parse_errors})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
