from __future__ import annotations

import argparse
from pathlib import Path

from lakehouse_mlops_aiops_lab.utils.s3util import (
    S3Config,
    ensure_bucket,
    make_s3_client,
)


def parse_args():
    p = argparse.ArgumentParser(description="Upload raw events file to MinIO(S3).")
    p.add_argument("--bucket", default="datalake")
    p.add_argument("--date", required=True, help="partition date YYYY-MM-DD")
    p.add_argument(
        "--infile", type=Path, required=True, help="path to local jsonl file"
    )
    p.add_argument("--prefix", default="raw/events", help="base prefix under bucket")
    p.add_argument("--name", default="events.jsonl", help="object filename")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    cfg = S3Config.from_env()
    s3 = make_s3_client(cfg)
    # Quick connectivity check
    try:
        s3.list_buckets()
    except Exception:
        print("ERROR: Cannot connect to S3 endpoint. Is Docker (MinIO) running?")
        return 2

    ensure_bucket(s3, args.bucket)

    key = f"{args.prefix}/dt={args.date}/{args.name}"
    s3.upload_file(str(args.infile), args.bucket, key)

    print(f"OK: uploaded {args.infile} to s3://{args.bucket}/{key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
