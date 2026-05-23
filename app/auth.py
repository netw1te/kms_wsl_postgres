from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from datetime import datetime

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.user import User

security = HTTPBasic(auto_error=False)

pwd_context = CryptContext(
    schemes=["bcrypt", "pbkdf2_sha256"],
    deprecated="auto",
)


@dataclass
class CurrentUser:
    id: int
    login: str
    full_name: Optional[str]
    email: Optional[str]
    is_user_admin: bool = False
    is_data_admin: bool = False    is_user_admin: bool = False
    is_data_admin: bool = False
    is_super_admin: bool = False

    is_super_admin: bool = False

    def can_manage_users(self) -> bool:
        return self.is_user_admin

    def can_manage_data(self) -> bool:
        return self.is_data_admin

    def can_manage_system(self) -> bool:
        return self.is_super_admin or self.is_super_admin

    def can_manage_users(self) -> bool:
        return self.is_super_admin or self.is_user_admin

    def can_manage_data(self) -> bool:
        return self.is_super_admin or self.is_data_admin

    def can_manage_system(self) -> bool:
        return self.is_super_admin


class PasswordEncoder:
    @staticmethod
    def encode(raw_password: str) -> str:
        return pwd_context.hash(raw_password)

    @staticmethod
    def hash(raw_password: str) -> str:
        return pwd_context.hash(raw_password)

    @staticmethod
    def verify(raw_password: str, encoded_password: str) -> bool:
        try:
            return pwd_context.verify(raw_password, encoded_password)
        except Exception:
            return False


def user_to_current_user(user: User) -> CurrentUser:
    return CurrentUser(
        id=user.id,
        login=user.login,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_user_admin=bool(getattr(user, "is_user_admin", False)),
        is_data_admin=bool(getattr(user, "is_data_admin", False)),
        is_super_admin=bool(getattr(user, "is_super_admin", False)),
    )


def user_has_active_access(user: User) -> bool:
    now = datetime.now()

    if user.access_start and user.access_start > now:
        return False

    if user.access_end and user.access_end < now:
        return False

    return True


def authenticate_user(
    db: Session,
    login: str,
    password: str,
) -> CurrentUser | None:
    user = db.query(User).filter(User.login == login).first()

    if user is None:
        return None

    if not PasswordEncoder.verify(password, user.password):
        return None

    if not user_has_active_access(user):
        return None

    return user_to_current_user(user)


async def get_current_user(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> CurrentUser:
    session_user = request.session.get("user")

    if session_user:
        user_id = session_user.get("id")
        user = db.query(User).filter(User.id == user_id).first()

        if user and user_has_active_access(user):
            return user_to_current_user(user)

    if credentials is not None:
        current_user = authenticate_user(
            db=db,
            login=credentials.username,
            password=credentials.password,
        )

        if current_user is not None:
            return current_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не авторизован",
        headers={"WWW-Authenticate": "Basic"},
    )


def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required.",
        )

    return current_user


async def require_user_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not current_user.can_manage_users():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User admin role required.",
        )

    return current_user


async def require_data_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not current_user.can_manage_data():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Data admin role required.",
        )

    return current_user


async def require_super_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not current_user.can_manage_system():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Super admin role required.",
        )

    return current_user