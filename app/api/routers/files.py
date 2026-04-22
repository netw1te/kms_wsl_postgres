from datetime import datetime

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.services.media_file_service import MediaFileService


router = APIRouter(prefix="/files", tags=["Вложения"])


class MediaFileResponse(BaseModel):
    id: int
    original_name: str
    stored_name: str
    content_type: str | None = None
    size_bytes: int
    checksum_sha256: str
    created_at: datetime
    uploaded_by: int | None = None


def to_response(item) -> MediaFileResponse:
    return MediaFileResponse(
        id=item.id,
        original_name=item.original_name,
        stored_name=item.stored_name,
        content_type=item.content_type,
        size_bytes=item.size_bytes,
        checksum_sha256=item.checksum_sha256,
        created_at=item.created_at,
        uploaded_by=item.uploaded_by,
    )


@router.get("/info-objects/{info_object_id}", response_model=list[MediaFileResponse])
async def list_info_object_files(
    info_object_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = MediaFileService(db)
    items = service.list_for_info_object(
        info_object_id=info_object_id,
        current_user_id=current_user.id,
        is_admin=current_user.is_admin(),
    )
    return [to_response(item) for item in items]


@router.post(
    "/info-objects/{info_object_id}",
    response_model=list[MediaFileResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_files_to_info_object(
    info_object_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = MediaFileService(db)
    items = await service.attach_files(
        info_object_id=info_object_id,
        files=files,
        current_user_id=current_user.id,
        is_admin=current_user.is_admin(),
    )
    return [to_response(item) for item in items]


@router.get("/info-objects/{info_object_id}/{file_id}/download")
async def download_file(
    info_object_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = MediaFileService(db)
    media_file = service.get_file_for_info_object(
        info_object_id=info_object_id,
        file_id=file_id,
        current_user_id=current_user.id,
        is_admin=current_user.is_admin(),
    )

    return FileResponse(
        path=media_file.file_path,
        media_type=media_file.content_type or "application/octet-stream",
        filename=media_file.original_name,
    )


@router.delete("/info-objects/{info_object_id}/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_file_from_info_object(
    info_object_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = MediaFileService(db)
    service.detach_file(
        info_object_id=info_object_id,
        file_id=file_id,
        current_user_id=current_user.id,
        is_admin=current_user.is_admin(),
    )