"""MinIO Object Storage Service."""

from __future__ import annotations

import io
from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings
from app.core.exceptions import StorageError

settings = get_settings()


class MinIOService:
    """Service wrapping MinIO SDK operations."""

    def __init__(self) -> None:
        self.client = Minio(
            endpoint=settings.minio.endpoint,
            access_key=settings.minio.access_key,
            secret_key=settings.minio.secret_key,
            secure=settings.minio.secure,
            region=settings.minio.region,
        )

    def ensure_bucket_exists(self, bucket_name: str) -> None:
        """Create bucket if it does not exist."""
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
        except S3Error as exc:
            raise StorageError(message=f"MinIO bucket error: {exc}") from exc

    def upload_file(
        self, bucket_name: str, object_name: str, file_data: bytes, content_type: str
    ) -> str:
        """Upload file bytes to MinIO bucket."""
        self.ensure_bucket_exists(bucket_name)
        try:
            stream = io.BytesIO(file_data)
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=stream,
                length=len(file_data),
                content_type=content_type,
            )
            return f"{bucket_name}/{object_name}"
        except S3Error as exc:
            raise StorageError(message=f"MinIO upload error: {exc}") from exc

    def get_file(self, bucket_name: str, object_name: str) -> bytes:
        """Download file bytes from MinIO."""
        try:
            response = self.client.get_object(bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as exc:
            raise StorageError(message=f"MinIO download error: {exc}") from exc

    def delete_file(self, bucket_name: str, object_name: str) -> None:
        """Remove file from bucket."""
        try:
            self.client.remove_object(bucket_name, object_name)
        except S3Error as exc:
            raise StorageError(message=f"MinIO delete error: {exc}") from exc
