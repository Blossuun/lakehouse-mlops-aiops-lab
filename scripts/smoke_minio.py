import os
import boto3
from botocore.exceptions import ClientError


def main() -> int:
    endpoint = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")

    if not access_key or not secret_key:
        print("Missing AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY in environment.")
        return 2

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-2"),
    )

    bucket = "mlflow-artifacts"
    key = "smoke/hello.txt"
    body = b"hello minio"

    # Create bucket if missing
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError:
        print(f"Bucket '{bucket}' not found. Creating...")
        s3.create_bucket(Bucket=bucket)

    # Put object
    s3.put_object(Bucket=bucket, Key=key, Body=body)

    # Get object and verify
    obj = s3.get_object(Bucket=bucket, Key=key)
    data = obj["Body"].read()
    assert data == body, f"Downloaded content mismatch: {data!r}"

    print("OK: MinIO S3 smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
