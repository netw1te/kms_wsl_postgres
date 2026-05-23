from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_super_admin
from app.database import get_db
from app.services.import_db_service import ImportDBService


router = APIRouter(prefix="/admin/import", tags=["Admin Import"])


class ImportResult(BaseModel):
    users: int = 0
    tags: int = 0
    info_objects: int = 0
    tag_links: int = 0
    user_agreements: int = 0
    search_queries: int = 0
    deletion_requests: int = 0
    media_files: int = 0
    attachments: int = 0


@router.post("/zip", response_model=ImportResult)
async def import_database_zip(
    file: UploadFile = File(...),
    current_admin: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Нужно загрузить ZIP-файл экспорта.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Файл пустой.")

    try:
        result = ImportDBService(db).import_zip(content)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Ошибка импорта: {exc}") from exc

    return ImportResult(**result)