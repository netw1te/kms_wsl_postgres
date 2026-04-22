from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.auth import require_admin, CurrentUser
from app.database import get_db
from app.services.export_db_service import ExportDBService

router = APIRouter(prefix="/admin/export", tags=["Admin Export"])

@router.get("/all")
async def export_all_databases(
    current_admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    service = ExportDBService(db)
    zip_data = service.export_all_databases()
    filename = f"kms_full_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return StreamingResponse(
        iter([zip_data]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/kms")
async def export_kms_databases(
    current_admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    service = ExportDBService(db)
    zip_data = service.export_kms_databases()
    filename = f"kms_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return StreamingResponse(
        iter([zip_data]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/user/{login}")
async def export_user_database(
    login: str,
    current_admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    service = ExportDBService(db)
    zip_data = service.export_user_database(login)
    if zip_data is None:
        raise HTTPException(status_code=404, detail=f"Пользователь {login} не найден")
    filename = f"kms_user_{login}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return StreamingResponse(
        iter([zip_data]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )