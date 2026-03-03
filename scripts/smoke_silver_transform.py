from __future__ import annotations

import os
import sys

import pyarrow as pa
import pyarrow.parquet as pq

from lakehouse_mlops_aiops_lab.utils.s3util import S3Config, list_keys, make_s3_client
from lakehouse_mlops_aiops_lab.transform.raw_to_silver_events import (
    main as transform_main,
)


def main() -> int:
    date = os.environ.get("SILVER_DATE", "2026-02-27")
    bucket = os.environ.get("SILVER_BUCKET", "datalake")
    raw_prefix = os.environ.get("RAW_PREFIX", "raw/events")
    silver_prefix = os.environ.get("SILVER_PREFIX", "silver/events")

    cfg = S3Config.from_env()
    s3 = make_s3_client(cfg)

    raw_prefix = f"{raw_prefix}/dt={date}/"
    raw_keys = [k for k in list_keys(s3, bucket, raw_prefix) if k.endswith(".jsonl")]
    if not raw_keys:
        print(f"FAIL: no raw jsonl found under s3://{bucket}/{raw_prefix}")
        return 2

    sys.argv = [
        "raw_to_silver_events",
        "--date",
        date,
        "--bucket",
        bucket,
        "--raw-prefix",
        raw_prefix,
        "--silver-prefix",
        silver_prefix,
        "--row-batch-size",
        "50000",
    ]
    rc = transform_main()
    if rc != 0:
        print(f"FAIL: transform returned {rc}")
        return rc

    silver_prefix = f"{silver_prefix}/dt={date}/"
    part_keys = [
        k for k in list_keys(s3, bucket, silver_prefix) if k.endswith(".parquet")
    ]
    if not part_keys:
        print(f"FAIL: no parquet parts found under s3://{bucket}/{silver_prefix}")
        return 3

    # Validate: read all parts and ensure event_id distinct
    all_event_ids: set[str] = set()
    total_rows = 0

    for key in sorted(part_keys):
        resp = s3.get_object(Bucket=bucket, Key=key)
        data = resp["Body"].read()
        table = pq.read_table(pa.BufferReader(data), columns=["event_id"])
        ids = table.column("event_id").to_pylist()
        total_rows += len(ids)

        for eid in ids:
            if eid in all_event_ids:
                print(f"FAIL: duplicate event_id found across parts: {eid}")
                return 4
            all_event_ids.add(eid)

    if total_rows <= 0:
        print("FAIL: total_rows is 0")
        return 5

    print(
        f"OK: silver transform smoke passed. parts={len(part_keys)} rows={total_rows}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
