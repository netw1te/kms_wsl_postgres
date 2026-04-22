from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import CurrentUser, PasswordEncoder, get_current_user, require_admin
from app.database import get_db
from app.models.user import User


router = APIRouter(prefix="/users", tags=["Пользователи"])


class UserResponse(BaseModel):
    id: int
    login: str
    full_name: str | None = None
    email: str | None = None
    role: str


class UserCreateByAdminRequest(BaseModel):
    login: str
    password: str
    full_name: str | None = None
    email: str | None = None
    role: str = "ROLE_USER"


def serialize_user(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        login=user.login,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
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
        role=current_user.role,
    )


@router.get("/info", response_model=UserResponse)
async def get_info(
    current_user: CurrentUser = Depends(get_current_user),
):
    return UserResponse(
        id=current_user.id,
        login=current_user.login,
        full_name=current_user.full_name,
        email=current_user.email,
        role=current_user.role,
    )


@router.get("", response_model=list[UserResponse])
async def get_all_users(
    db: Session = Depends(get_db),
    current_admin: CurrentUser = Depends(require_admin),
):
    users = db.query(User).order_by(User.id.asc()).all()
    return [serialize_user(user) for user in users]


@router.post("/admin-create", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_by_admin(
    payload: UserCreateByAdminRequest,
    db: Session = Depends(get_db),
    current_admin: CurrentUser = Depends(require_admin),
):
    login = payload.login.strip()
    password = payload.password.strip()
    role = payload.role.strip()

    if not login:
        raise HTTPException(status_code=400, detail="Логин обязателен.")
    if not password:
        raise HTTPException(status_code=400, detail="Пароль обязателен.")
    if role not in {"ROLE_USER", "ROLE_ADMIN"}:
        raise HTTPException(status_code=400, detail="Недопустимая роль.")

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
        role=role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return serialize_user(user)