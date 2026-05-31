"""Storage abstraction. Default backend is Backblaze B2 (S3-compatible).

Switching backends requires no call-site changes: callers depend only on the
``StorageBackend`` protocol and obtain a concrete instance via ``get_storage()``.
"""

from __future__ import annotations

import abc
import os
from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageBackend(abc.ABC):
    @abc.abstractmethod
    def save(self, key: str, data: bytes, content_type: str) -> None: ...

    @abc.abstractmethod
    def delete(self, key: str) -> None: ...

    @abc.abstractmethod
    def url(self, key: str) -> str:
        """Return a (possibly presigned/time-limited) URL to download the object."""


class B2Storage(StorageBackend):
    """Backblaze B2 via its S3-compatible API using boto3."""

    def __init__(self) -> None:
        import boto3  # imported lazily so the app starts without boto3 in local mode
        from botocore.config import Config

        if not all(
            [settings.B2_KEY_ID, settings.B2_APPLICATION_KEY, settings.B2_BUCKET_NAME, settings.B2_ENDPOINT_URL]
        ):
            raise RuntimeError(
                "Backblaze B2 is not fully configured. Set B2_KEY_ID, B2_APPLICATION_KEY, "
                "B2_BUCKET_NAME and B2_ENDPOINT_URL, or set STORAGE_BACKEND=local."
            )

        self.bucket = settings.B2_BUCKET_NAME
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.B2_ENDPOINT_URL,
            aws_access_key_id=settings.B2_KEY_ID,
            aws_secret_access_key=settings.B2_APPLICATION_KEY,
            region_name=settings.B2_REGION,
            config=Config(signature_version="s3v4"),
        )

    def save(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=self.bucket, Key=key, Body=data, ContentType=content_type
        )

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)

    def url(self, key: str) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=settings.PRESIGNED_URL_EXPIRE_SECONDS,
        )


class LocalStorage(StorageBackend):
    """Filesystem fallback for offline/local development."""

    def __init__(self) -> None:
        self.base = Path(settings.LOCAL_STORAGE_DIR)
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = self.base / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def save(self, key: str, data: bytes, content_type: str) -> None:
        self._path(key).write_bytes(data)

    def delete(self, key: str) -> None:
        try:
            os.remove(self._path(key))
        except FileNotFoundError:
            pass

    def url(self, key: str) -> str:
        # Served via the local download endpoint (see attachments router).
        return f"{settings.API_V1_PREFIX}/attachments/local/{key}"

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()


@lru_cache
def get_storage() -> StorageBackend:
    backend = settings.STORAGE_BACKEND.lower()
    if backend == "local":
        logger.info("Using LocalStorage backend")
        return LocalStorage()
    logger.info("Using Backblaze B2 storage backend")
    return B2Storage()
