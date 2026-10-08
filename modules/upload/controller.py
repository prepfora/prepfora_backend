from fastapi import APIRouter, Depends, File, Form, UploadFile
from common.classes.return_type import ReturnType
from modules.upload.schema import FileUploadResponse
from modules.upload.service import UploadService, get_upload_service

router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
    responses={404: {"description": "Not found"}},
)


@router.post("", response_model=ReturnType[FileUploadResponse], status_code=201)
@router.post("/file", response_model=ReturnType[FileUploadResponse], status_code=201)
async def upload_file(
    file: UploadFile = File(..., description="File to upload to AWS S3"),
    folder: str = Form("uploads", description="Target folder/prefix in the S3 bucket"),
    service: UploadService = Depends(get_upload_service),
) -> ReturnType[FileUploadResponse]:
    return await service.upload_file(file=file, folder=folder)


@router.post("/multiple", response_model=ReturnType[list[FileUploadResponse]], status_code=201)
async def upload_multiple_files(
    files: list[UploadFile] = File(..., description="List of files to upload to AWS S3"),
    folder: str = Form("uploads", description="Target folder/prefix in the S3 bucket"),
    service: UploadService = Depends(get_upload_service),
) -> ReturnType[list[FileUploadResponse]]:
    return await service.upload_multiple_files(files=files, folder=folder)
