from __future__ import annotations

import os
from pathlib import Path

from lakehouse_mlops_aiops_lab.ingest.generate_events import (
    GenConfig,
    generate_events,
    write_jsonl,
)
from lakehouse_mlops_aiops_lab.utils.s3util import (
    S3Config,
    ensure_bucket,
    make_s3_client,
)


def count_lines(p: Path) -> int:
    with p.open("r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def main() -> int:
    # Inputs
    date = os.environ.get("RAW_DATE", "2026-02-27")
    bucket = os.environ.get("RAW_BUCKET", "datalake")
    prefix = os.environ.get("RAW_PREFIX", "raw/events")
    out = Path("./tmp/smoke_events.jsonl")

    cfg = GenConfig(
        date=date,
        rows=2000,
        out=out,
        seed=7,
        purchase_rate=0.015,
        late_rate=0.05,
        duplicate_rate=0.005,
        dirty_rate=0.01,
        schema_v2_rate=0.20,
    )

    # Generate
    events = generate_events(cfg)
    write_jsonl(events, out)
    local_lines = count_lines(out)
    if local_lines <= 0:
        print("FAIL: generated 0 lines")
        return 2

    # Upload
    s3cfg = S3Config.from_env()
    s3 = make_s3_client(s3cfg)
    ensure_bucket(s3, bucket)

    key = f"{prefix}/dt={date}/events-smoke.jsonl"
    s3.upload_file(str(out), bucket, key)

    # Download to verify
    download_path = Path("./tmp/smoke_download.jsonl")
    download_path.parent.mkdir(parents=True, exist_ok=True)
    s3.download_file(bucket, key, str(download_path))

    remote_lines = count_lines(download_path)
    if remote_lines != local_lines:
        print(f"FAIL: line count mismatch local={local_lines}, remote={remote_lines}")
        return 3

    print(f"OK: raw ingest smoke passed. s3://{bucket}/{key} lines={remote_lines}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
