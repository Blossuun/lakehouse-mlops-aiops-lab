from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import boto3


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
            raise RuntimeError(f"Missing {access_key_env}/{secret_key_env} in environment.")
        return S3Config(endpoint_url=endpoint, access_key_id=ak, secret_access_key=sk, region=region)


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