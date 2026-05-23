from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.auth import CurrentUser, PasswordEncoder, get_current_user, require_user_admin
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Пользователи"])


class UserResponse(BaseModel):
    id: int
    login: str
    full_name: str | None = None
    email: str | None = None
    is_user_admin: bool = False
    is_data_admin: bool = False
    is_super_admin: bool = False


class UserCreateByAdminRequest(BaseModel):
    login: str
    password: str
    full_name: str | None = None
    email: str | None = None
    is_user_admin: bool = False
    is_data_admin: bool = False
    is_super_admin: bool = False


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    access_start: Optional[str] = None
    access_end: Optional[str] = None
    is_user_admin: Optional[bool] = None
    is_data_admin: Optional[bool] = None
    is_super_admin: Optional[bool] = None


def serialize_user(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        login=user.login,
        full_name=user.full_name,
        email=user.email,
        is_user_admin=user.is_user_admin or False,
        is_data_admin=user.is_data_admin or False,
        is_super_admin=user.is_super_admin or False,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
        current_user: CurrentUser = Depends(get_current_user),
):
    return UserResponse(
        id=current_user.id,
        login=current_user.login,
        full_name=current_user.full_name,
        email=current_user.email,
        is_user_admin=current_user.is_user_admin,
        is_data_admin=current_user.is_data_admin,
        is_super_admin=current_user.is_super_admin,
    )


@router.get("", response_model=list[UserResponse])
async def get_all_users(
        db: Session = Depends(get_db),
        current_admin: CurrentUser = Depends(require_user_admin),
):
    users = db.query(User).order_by(User.id.asc()).all()
    return [serialize_user(user) for user in users]


@router.post("/admin-create", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_by_admin(
        payload: UserCreateByAdminRequest,
        db: Session = Depends(get_db),
        current_admin: CurrentUser = Depends(require_user_admin),
):
    login = payload.login.strip()
    password = payload.password.strip()

    if not login:
        raise HTTPException(status_code=400, detail="Логин обязателен.")
    if not password:
        raise HTTPException(status_code=400, detail="Пароль обязателен.")

    existing_login = db.query(User).filter(User.login == login).first()
    if existing_login:
        raise HTTPException(status_code=409, detail="Пользователь с таким логином уже существует.")

    if payload.email:
        existing_email = db.query(User).filter(User.email == payload.email).first()
        if existing_email:
            raise HTTPException(status_code=409, detail="Пользователь с таким email уже существует.")

    user = User(
        login=login,
        password=PasswordEncoder.hash(password),
        full_name=payload.full_name.strip() if payload.full_name else None,
        email=payload.email.strip() if payload.email else None,
        is_user_admin=payload.is_user_admin,
        is_data_admin=payload.is_data_admin,
        is_super_admin=payload.is_super_admin,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return serialize_user(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
        user_id: int,
        payload: UserUpdateRequest,
        db: Session = Depends(get_db),
        current_admin: CurrentUser = Depends(require_user_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.email is not None:
        user.email = payload.email
    if payload.access_start is not None:
        user.access_start = datetime.fromisoformat(payload.access_start) if payload.access_start else None
    if payload.access_end is not None:
        user.access_end = datetime.fromisoformat(payload.access_end) if payload.access_end else None
    if payload.is_user_admin is not None:
        user.is_user_admin = payload.is_user_admin
    if payload.is_data_admin is not None:
        user.is_data_admin = payload.is_data_admin
    if payload.is_super_admin is not None:
        user.is_super_admin = payload.is_super_admin

    db.commit()
    db.refresh(user)

    return serialize_user(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_admin: CurrentUser = Depends(require_user_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    db.delete(user)
    db.commit()


@router.post("/{user_id}/block")
async def block_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_admin: CurrentUser = Depends(require_user_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.access_end = datetime(1970, 1, 1)
    db.commit()

    return {"message": "User blocked", "user_id": user_id}


@router.post("/{user_id}/unblock")
async def unblock_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_admin: CurrentUser = Depends(require_user_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.access_end = None
    db.commit()

    return {"message": "User unblocked", "user_id": user_id}