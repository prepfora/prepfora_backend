import asyncio
import os
import re
import uuid
import mimetypes
from typing import Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile

from common.classes.return_type import ReturnType
from common.config import settings
from common.exceptions.bad_request_exception import BadRequestException
from common.exceptions.internal_server_exception import InternalServerException
from common.logger import logger
from modules.upload.schema import FileUploadResponse


class UploadService:
    def __init__(
        self,
        access_key_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        region_name: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ):
        self.access_key_id = access_key_id or settings.aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID", "")
        self.secret_key = (
            secret_key
            or settings.aws_secret_key
            or os.getenv("AWS_SECRET_KEY", "")
            or os.getenv("AWS_SECRET_ACCESS_KEY", "")
        )
        self.region_name = region_name or settings.aws_region or os.getenv("AWS_REGION", "eu-north-1")
        self.bucket_name = bucket_name or settings.aws_bucket_name or os.getenv("AWS_BUCKET_NAME", "ryzly-apps")

        if not self.access_key_id or not self.secret_key or not self.bucket_name:
            logger.warning("AWS S3 credentials or bucket name are not fully configured.")

    def _get_s3_client(self):
        return boto3.client(
            "s3",
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_key,
            region_name=self.region_name,
        )

    def _generate_s3_url(self, key: str) -> str:
        # Standard virtual-hosted-style URL for AWS S3
        return f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{key}"

    def _sanitize_filename(self, filename: str) -> str:
        clean_name = os.path.basename(filename)
        # Replace non-alphanumeric chars (except dot, dash, underscore) with underscore
        clean_name = re.sub(r"[^a-zA-Z0-9._-]", "_", clean_name)
        return clean_name or "file"

    def _generate_key(self, filename: str, folder: str = "uploads") -> str:
        sanitized = self._sanitize_filename(filename)
        unique_prefix = uuid.uuid4().hex
        folder_clean = folder.strip("/").strip()
        if folder_clean:
            return f"{folder_clean}/{unique_prefix}_{sanitized}"
        return f"{unique_prefix}_{sanitized}"

    def _upload_sync(self, body: bytes, key: str, content_type: str) -> None:
        client = self._get_s3_client()
        client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=body,
            ContentType=content_type,
        )

    async def upload_file(
        self,
        file: UploadFile,
        folder: str = "uploads",
    ) -> ReturnType[FileUploadResponse]:
        if not file or not file.filename:
            logger.error("No file provided for upload.")
            raise BadRequestException("A valid file must be provided.")

        try:
            content = await file.read()
            if not content:
                logger.error("Attempted to upload an empty file.")
                raise BadRequestException("File content cannot be empty.")

            content_type = file.content_type
            if not content_type or content_type == "application/octet-stream":
                guessed_type, _ = mimetypes.guess_type(file.filename)
                if guessed_type:
                    content_type = guessed_type
                else:
                    content_type = "application/octet-stream"

            key = self._generate_key(file.filename, folder=folder)

            logger.info(f"Uploading file '{file.filename}' to S3 bucket '{self.bucket_name}' with key '{key}'")

            # Run blocking boto3 put_object in a separate thread
            await asyncio.to_thread(self._upload_sync, content, key, content_type)

            complete_url = self._generate_s3_url(key)
            logger.info(f"File uploaded successfully to S3: {complete_url}")

            response_data = FileUploadResponse(
                url=complete_url,
                key=key,
                file_name=file.filename,
                content_type=content_type,
                size=len(content),
            )

            return ReturnType[FileUploadResponse](
                success=True,
                message="File uploaded successfully",
                data=response_data,
            )

        except (BadRequestException, InternalServerException):
            raise
        except (BotoCoreError, ClientError) as e:
            logger.error(f"AWS S3 error during upload: {str(e)}")
            raise InternalServerException(f"AWS S3 upload failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during file upload: {str(e)}")
            raise InternalServerException(f"Failed to upload file: {str(e)}")
        finally:
            await file.seek(0)

    async def upload_multiple_files(
        self,
        files: list[UploadFile],
        folder: str = "uploads",
    ) -> ReturnType[list[FileUploadResponse]]:
        if not files:
            raise BadRequestException("At least one file must be provided.")

        uploaded_items: list[FileUploadResponse] = []
        for file in files:
            result = await self.upload_file(file, folder=folder)
            if result.data:
                uploaded_items.append(result.data)

        return ReturnType[list[FileUploadResponse]](
            success=True,
            message="All files uploaded successfully",
            data=uploaded_items,
        )

    async def upload_bytes(
        self,
        data: bytes,
        filename: str,
        content_type: Optional[str] = None,
        folder: str = "uploads",
    ) -> ReturnType[FileUploadResponse]:
        if not data:
            raise BadRequestException("Data cannot be empty.")

        try:
            if not content_type:
                guessed_type, _ = mimetypes.guess_type(filename)
                content_type = guessed_type or "application/octet-stream"

            key = self._generate_key(filename, folder=folder)

            await asyncio.to_thread(self._upload_sync, data, key, content_type)

            complete_url = self._generate_s3_url(key)

            return ReturnType[FileUploadResponse](
                success=True,
                message="File uploaded successfully",
                data=FileUploadResponse(
                    url=complete_url,
                    key=key,
                    file_name=filename,
                    content_type=content_type,
                    size=len(data),
                ),
            )
        except Exception as e:
            logger.error(f"Error uploading bytes: {str(e)}")
            raise InternalServerException(f"Upload failed: {str(e)}")


def get_upload_service() -> UploadService:
    return UploadService()
