from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user, require_admin
from app.database import get_db
from app.schemas.user import UserResponse
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["Пользователи"])


@router.get("/is-admin")
async def is_admin(
    login: str = Query(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = UserService(db)
    return {"login": login, "is_admin": service.is_admin_by_login(login)}


@router.get("/{user_id}/is-admin")
async def is_admin_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = UserService(db)
    return {"id": user_id, "is_admin": service.is_admin_by_id(user_id)}


@router.get("/info", response_model=UserResponse)
async def get_info(
    login: str = Query(...),
    db: Session = Depends(get_db),
    current_admin: CurrentUser = Depends(require_admin),
):
    service = UserService(db)
    user = service.get_info_by_login(login)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user.id,
        login=user.login,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
    )