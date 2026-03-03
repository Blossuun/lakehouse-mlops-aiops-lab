from __future__ import annotations

import os
from dataclasses import dataclass

import boto3

from typing import Iterable


@dataclass(frozen=True)
class S3Config:
    endpoint_url: str
    access_key_id: str
    secret_access_key: str
    region: str

    @staticmethod
    def from_env(
        endpoint_env: str = "MINIO_ENDPOINT",
        access_key_env: str = "AWS_ACCESS_KEY_ID",
        secret_key_env: str = "AWS_SECRET_ACCESS_KEY",
        region_env: str = "AWS_DEFAULT_REGION",
        default_endpoint: str = "http://localhost:9000",
        default_region: str = "ap-northeast-2",
    ) -> "S3Config":
        endpoint = os.environ.get(endpoint_env, default_endpoint)
        ak = os.environ.get(access_key_env)
        sk = os.environ.get(secret_key_env)
        region = os.environ.get(region_env, default_region)
        if not ak or not sk:
            raise RuntimeError(
                f"Missing {access_key_env}/{secret_key_env} in environment."
            )
        return S3Config(
            endpoint_url=endpoint, access_key_id=ak, secret_access_key=sk, region=region
        )


def make_s3_client(cfg: S3Config):
    return boto3.client(
        "s3",
        endpoint_url=cfg.endpoint_url,
        aws_access_key_id=cfg.access_key_id,
        aws_secret_access_key=cfg.secret_access_key,
        region_name=cfg.region,
    )


def ensure_bucket(s3, bucket: str) -> None:
    """
    Create bucket if it doesn't exist.
    For MinIO, create_bucket usually works without region constraints.
    """
    try:
        s3.head_bucket(Bucket=bucket)
        return
    except Exception:
        s3.create_bucket(Bucket=bucket)


def list_keys(s3, bucket: str, prefix: str) -> list[str]:
    """List object keys under prefix."""
    keys: list[str] = []
    token = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            keys.append(obj["Key"])
        if resp.get("IsTruncated"):
            token = resp.get("NextContinuationToken")
        else:
            break
    return keys


def get_text(s3, bucket: str, key: str, encoding: str = "utf-8") -> str:
    resp = s3.get_object(Bucket=bucket, Key=key)
    return resp["Body"].read().decode(encoding)


def put_bytes(
    s3,
    bucket: str,
    key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> None:
    s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)


def iter_lines(s3, bucket: str, key: str) -> Iterable[bytes]:
    """
    Stream object content line by line as bytes.
    Suitable for JSONL without loading whole file into memory.
    """
    resp = s3.get_object(Bucket=bucket, Key=key)
    body = resp["Body"]
    # botocore supports iter_lines()
    for line in body.iter_lines():
        yield line


def delete_keys(s3, bucket: str, keys: list[str]) -> None:
    """Delete up to 1000 keys per request (S3 API limit)."""
    if not keys:
        return
    # batch delete
    for i in range(0, len(keys), 1000):
        chunk = keys[i : i + 1000]
        s3.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": k} for k in chunk], "Quiet": True},
        )


def delete_parquet_under_prefix(s3, bucket: str, prefix: str) -> int:
    """Delete *.parquet objects under prefix. Returns deleted count."""
    keys = [k for k in list_keys(s3, bucket, prefix) if k.endswith(".parquet")]
    delete_keys(s3, bucket, keys)
    return len(keys)
