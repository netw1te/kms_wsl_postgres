from dataclasses import dataclass
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
    is_data_admin: bool = False
    is_super_admin: bool = False

    def can_manage_users(self) -> bool:
        return self.is_user_admin

    def can_manage_data(self) -> bool:
        return self.is_data_admin

    def can_manage_system(self) -> bool:
        return self.is_super_admin


class PasswordEncoder:
    @staticmethod
    def encode(raw_password: str) -> str:
        return pwd_context.hash(raw_password)

    @staticmethod
    def verify(raw_password: str, encoded_password: str) -> bool:
        return pwd_context.verify(raw_password, encoded_password)

    @staticmethod
    def hash(raw_password: str) -> str:
        return pwd_context.hash(raw_password)


def authenticate_user(db: Session, username: str, password: str) -> CurrentUser | None:
    user = db.query(User).filter(User.login == username).first()
    if user is None:
        return None
    if not PasswordEncoder.verify(password, user.password):
        return None

    now = datetime.now()
    if user.access_start and user.access_start > now:
        return None
    if user.access_end and user.access_end < now:
        return None

    return CurrentUser(
        id=user.id,
        login=user.login,
        full_name=user.full_name,
        email=user.email,
        is_user_admin=user.is_user_admin or False,
        is_data_admin=user.is_data_admin or False,
        is_super_admin=user.is_super_admin or False,
    )


async def get_current_user(
        credentials: HTTPBasicCredentials | None = Depends(security),
        request: Request = None,
        db: Session = Depends(get_db),
):
    if credentials:
        user = authenticate_user(db, credentials.username, credentials.password)
        if user:
            return user

    if request:
        session_user = request.session.get("user")
        if session_user:
            user_id = session_user.get("id")
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return CurrentUser(
                    id=user.id,
                    login=user.login,
                    full_name=user.full_name,
                    email=user.email,
                    is_user_admin=user.is_user_admin or False,
                    is_data_admin=user.is_data_admin or False,
                    is_super_admin=user.is_super_admin or False,
                )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не авторизован",
    )


def require_user_admin(current_user: CurrentUser = Depends(get_current_user)):
    if not current_user.can_manage_users():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User admin role required.",
        )
    return current_user


def require_data_admin(current_user: CurrentUser = Depends(get_current_user)):
    if not current_user.can_manage_data():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Data admin role required.",
        )
    return current_user


def require_super_admin(current_user: CurrentUser = Depends(get_current_user)):
    if not current_user.can_manage_system():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Super admin role required.",
        )
    return current_user