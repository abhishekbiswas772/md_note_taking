import io
from minio import Minio
from datetime import timedelta
import uuid
from typing import Optional
import os
import logging
from dotenv import load_dotenv
import json

load_dotenv()

logger = logging.getLogger(__name__)


class MinioService:
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT")
        self.access_key = os.getenv("MINIO_ACCESS_KEY")
        self.secret_key = os.getenv("MINIO_SECRET_KEY")
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME")
        self.secure = os.getenv("MINIO_SECURE", "true").lower() == "true"

        self.client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)

        self._set_public_bucket_policy()

    class MinioException(Exception):
        pass

    def _set_public_bucket_policy(self):
        try:
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                    }
                ]
            }
            self.client.set_bucket_policy(self.bucket_name, json.dumps(policy))
            logger.info(f"Set public read policy for bucket '{self.bucket_name}'")
        except Exception as e:
            logger.warning(f"Failed to set bucket policy: {str(e)}")

    def upload_to_minio(self, file_stream: io.BytesIO, file_name: Optional[str] = None, max_size_mb: int = 10) -> str:
        try:
            file_stream.seek(0)
            size = file_stream.getbuffer().nbytes

            max_size_bytes = max_size_mb * 1024 * 1024
            if size > max_size_bytes:
                raise self.MinioException(f"File size ({size} bytes) exceeds maximum allowed ({max_size_bytes} bytes)")

            if size == 0:
                raise self.MinioException("File is empty")

            object_name = file_name or f"notes/{uuid.uuid4()}.md"

            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_stream,
                length=size,
                content_type="text/markdown",
            )

            logger.info(f"Uploaded '{object_name}' to bucket '{self.bucket_name}'")

            return self.get_public_url(object_name)
        except self.MinioException:
            raise
        except Exception as e:
            raise self.MinioException(f"Upload failed: {str(e)}")

    def get_public_url(self, file_name: str, expires_minutes: int = 0) -> str:
        try:
            if expires_minutes > 0:
                return self.client.presigned_get_object(
                    bucket_name=self.bucket_name,
                    object_name=file_name,
                    expires=timedelta(minutes=expires_minutes)
                )
            else:
                scheme = "https" if self.secure else "http"
                return f"{scheme}://{self.endpoint}/{self.bucket_name}/{file_name}"
        except Exception as e:
            raise self.MinioException(f"Failed to generate public URL: {str(e)}")

    def delete_from_minio(self, object_name: str) -> bool:
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            logger.info(f"Deleted '{object_name}' from bucket '{self.bucket_name}'")
            return True
        except Exception as e:
            raise self.MinioException(f"Delete failed: {str(e)}")
