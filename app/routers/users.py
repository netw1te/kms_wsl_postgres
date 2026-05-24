from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    CurrentUser,
    PasswordEncoder,
    get_current_user,
    require_user_admin,
)
from app.database import get_db
from app.models.user import User
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["Пользователи"])


class UserResponse(BaseModel):
    id: int
    login: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: str

    access_start: Optional[datetime] = None
    access_end: Optional[datetime] = None

    is_user_admin: bool = False
    is_data_admin: bool = False
    is_super_admin: bool = False


class AdminCreateUserRequest(BaseModel):
    login: str
    password: str
    full_name: Optional[str] = None
    email: Optional[str] = None

    role: Optional[str] = None

    access_start: Optional[datetime] = None
    access_end: Optional[datetime] = None

    is_user_admin: bool = False
    is_data_admin: bool = False
    is_super_admin: bool = False


def role_from_flags(
    *,
    role: Optional[str] = None,
    is_user_admin: bool = False,
    is_data_admin: bool = False,
    is_super_admin: bool = False,
) -> str:
    if role == "ROLE_ADMIN":
        return "ROLE_ADMIN"

    if is_user_admin or is_data_admin or is_super_admin:
        return "ROLE_ADMIN"

    return "ROLE_USER"


def serialize_user(user: User) -> UserResponse:
    role_val = getattr(user, "role", "ROLE_USER")
    if role_val == "ROLE_USER" and (user.is_user_admin or user.is_data_admin or user.is_super_admin):
        role_val = "ROLE_ADMIN"

    return UserResponse(
        id=user.id,
        login=user.login,
        full_name=user.full_name,
        email=user.email,
        role=role_val,
        access_start=getattr(user, "access_start", None),
        access_end=getattr(user, "access_end", None),
        is_user_admin=bool(getattr(user, "is_user_admin", False)),
        is_data_admin=bool(getattr(user, "is_data_admin", False)),
        is_super_admin=bool(getattr(user, "is_super_admin", False)),
    )


def table_exists(db: Session, table_name: str) -> bool:
    return db.execute(
        text("SELECT to_regclass(:table_name)"),
        {"table_name": table_name},
    ).scalar() is not None


def column_exists(db: Session, table_name: str, column_name: str) -> bool:
    return bool(
        db.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = :table_name
                      AND column_name = :column_name
                )
                """
            ),
            {
                "table_name": table_name,
                "column_name": column_name,
            },
        ).scalar()
    )


def delete_refs(db: Session, table_name: str, column_name: str, user_id: int) -> None:
    if table_exists(db, table_name) and column_exists(db, table_name, column_name):
        db.execute(
            text(f"DELETE FROM {table_name} WHERE {column_name} = :user_id"),
            {"user_id": user_id},
        )


def null_refs(db: Session, table_name: str, column_name: str, user_id: int) -> None:
    if table_exists(db, table_name) and column_exists(db, table_name, column_name):
        db.execute(
            text(f"UPDATE {table_name} SET {column_name} = NULL WHERE {column_name} = :user_id"),
            {"user_id": user_id},
        )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return serialize_user(current_user)


@router.get("", response_model=list[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    current_admin: CurrentUser = Depends(require_user_admin),
):
    users = db.query(User).order_by(User.id.asc()).all()
    return [serialize_user(user) for user in users]


@router.post("/admin-create", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_by_admin(
    payload: AdminCreateUserRequest,
    db: Session = Depends(get_db),
    current_admin: CurrentUser = Depends(require_user_admin),
):
    login = payload.login.strip()

    if not login:
        raise HTTPException(status_code=400, detail="Логин не может быть пустым.")

    if not payload.password:
        raise HTTPException(status_code=400, detail="Пароль не может быть пустым.")

    existing = db.query(User).filter(User.login == login).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Пользователь с таким логином уже существует.",
        )

    user = User(
        login=login,
        password=PasswordEncoder.hash(payload.password),
        full_name=payload.full_name.strip() if payload.full_name else None,
        email=payload.email.strip() if payload.email else None,
        access_start=payload.access_start,
        access_end=payload.access_end,
        is_user_admin=payload.is_user_admin,
        is_data_admin=payload.is_data_admin,
        is_super_admin=payload.is_super_admin,
    )

    if hasattr(user, "role"):
        user.role = role_from_flags(
            role=payload.role,
            is_user_admin=payload.is_user_admin,
            is_data_admin=payload.is_data_admin,
            is_super_admin=payload.is_super_admin,
        )

    db.add(user)
    db.commit()
    db.refresh(user)

    return serialize_user(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: CurrentUser = Depends(require_user_admin),
):
    if current_admin.id == user_id:
        raise HTTPException(
            status_code=400,
            detail="Нельзя удалить текущего пользователя.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if bool(getattr(user, "is_super_admin", False)):
        super_admins_count = (
            db.query(User)
            .filter(User.is_super_admin.is_(True))
            .count()
        )
        if super_admins_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Нельзя удалить последнего суперадминистратора.",
            )

    try:
        delete_refs(db, "user_agreements", "user_id", user_id)

        delete_refs(db, "search_queries", "user_id", user_id)
        delete_refs(db, "search_queries", "created_by", user_id)

        delete_refs(db, "info_object_deletion_requests", "requested_by", user_id)

        null_refs(db, "info_object_deletion_requests", "reviewed_by", user_id)

        null_refs(db, "information_objects", "created_by", user_id)
        null_refs(db, "information_objects", "deleted_by", user_id)

        null_refs(db, "media_files", "uploaded_by", user_id)

        db.execute(
            text("DELETE FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        )

        db.commit()

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "Пользователь связан с другой таблицей. "
                "Удаление остановлено, чтобы не повредить данные."
            ),
        ) from exc


@router.get("/is-admin")
async def is_admin(
    login: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = UserService(db)
    return {"login": login, "is_admin": service.is_admin_by_login(login)}


@router.get("/info", response_model=UserResponse)
async def get_info(
    login: str = Query(...),
    db: Session = Depends(get_db),
    current_admin: CurrentUser = Depends(require_user_admin),
):
    service = UserService(db)
    user = service.get_info_by_login(login)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return serialize_user(user)


@router.get("/{user_id}/is-admin")
async def is_admin_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = UserService(db)
    return {"id": user_id, "is_admin": service.is_admin_by_id(user_id)}