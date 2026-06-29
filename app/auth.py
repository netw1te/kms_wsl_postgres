from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
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
    role: str = "ROLE_USER"
    is_user_admin: bool = False
    is_data_admin: bool = False
    is_super_admin: bool = False
    access_start: Optional[datetime] = None
    access_end: Optional[datetime] = None

    @property
    def authorities(self) -> list[str]:
        return [self.role]

    def is_admin(self) -> bool:
        return self.is_super_admin or self.is_user_admin or self.is_data_admin or self.role == "ROLE_ADMIN"

    def can_manage_users(self) -> bool:
        return self.is_user_admin or self.is_super_admin

    def can_manage_data(self) -> bool:
        return self.is_data_admin or self.is_super_admin

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
    is_user_admin = bool(getattr(user, "is_user_admin", False))
    is_data_admin = bool(getattr(user, "is_data_admin", False))
    is_super_admin = bool(getattr(user, "is_super_admin", False))
    db_role = getattr(user, "role", "ROLE_USER")
    if db_role == "ROLE_ADMIN" or is_user_admin or is_data_admin or is_super_admin:
        legacy_role = "ROLE_ADMIN"
    else:
        legacy_role = "ROLE_USER"
    return CurrentUser(
        id=user.id,
        login=user.login,
        full_name=getattr(user, "full_name", None),
        email=getattr(user, "email", None),
        role=legacy_role,
        is_user_admin=is_user_admin,
        is_data_admin=is_data_admin,
        is_super_admin=is_super_admin,
        access_start=getattr(user, "access_start", None),
        access_end=getattr(user, "access_end", None),
    )


def user_has_active_access(user: User) -> bool:
    now = datetime.now()

    access_start = getattr(user, "access_start", None)
    access_end = getattr(user, "access_end", None)

    if access_start and access_start > now:
        return False

    if access_end and access_end < now:
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