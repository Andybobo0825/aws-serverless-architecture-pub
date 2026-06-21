from __future__ import annotations

from typing import Any

from magic_api.errors import BadRequest


def create_presigned_get_url(
    s3_client: Any, *, bucket: str, key: str | None, expires_in: int
) -> str:
    if not key:
        raise BadRequest("content key is not configured")
    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )
    return str(url)


def create_presigned_put_url(
    s3_client: Any,
    *,
    bucket: str,
    key: str,
    expires_in: int = 300,
    content_type: str = "application/pdf",
) -> str:
    if not key:
        raise BadRequest("upload key is required")
    url = s3_client.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=expires_in,
    )
    return str(url)


def list_object_keys(s3_client: Any, *, bucket: str, prefixes: tuple[str, ...]) -> list[str]:
    keys: list[str] = []
    for prefix in prefixes:
        continuation_token: str | None = None
        while True:
            kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token
            response = s3_client.list_objects_v2(**kwargs)
            for item in response.get("Contents", []):
                if isinstance(item, dict) and isinstance(item.get("Key"), str):
                    key = item["Key"]
                    if not key.endswith("/"):
                        keys.append(key)
            if not response.get("IsTruncated"):
                break
            continuation_token = response.get("NextContinuationToken")
            if not isinstance(continuation_token, str):
                break
    return sorted(keys)
