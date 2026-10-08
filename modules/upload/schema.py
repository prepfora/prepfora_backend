from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    url: str = Field(description="Complete public URL of the uploaded file on S3")
    key: str = Field(description="S3 object key")
    file_name: str = Field(description="Original file name")
    content_type: str = Field(description="MIME type of the file")
    size: int = Field(description="File size in bytes")
