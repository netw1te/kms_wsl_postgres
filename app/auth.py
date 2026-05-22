from dataclasses import dataclass
from typing import Optional
from app.database import SessionLocal


from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.database import SessionLocal
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
    role: str

    @property
    def authorities(self) -> list[str]:
        return [item.strip() for item in self.role.split(",") if item.strip()]

    def is_admin(self) -> bool:
        return "ROLE_ADMIN" in self.authorities


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


from datetime import datetime

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
        role=user.role,
    )

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User

security = HTTPBasic(auto_error=False)


class PasswordEncoder:
    @staticmethod
    def hash(raw_password: str) -> str:
        return pwd_context.hash(raw_password)

    @staticmethod
    def verify(raw_password: str, encoded_password: str) -> bool:
        return pwd_context.verify(raw_password, encoded_password)


from datetime import datetime

def authenticate_user(db: Session, login: str, password: str):
    user = db.query(User).filter(User.login == login).first()
    if not user:
        return None

    if not PasswordEncoder.verify(password, user.password):
        return None

    now = datetime.now()

    if user.access_start and user.access_start > now:
        return None

    if user.access_end and user.access_end < now:
        return None

    return user


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
):
    session_user = request.session.get("user")
    if session_user:
        user_id = session_user.get("id")
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не авторизован",
    )


def require_admin(current_user=Depends(get_current_user)):
    if current_user.role != "ROLE_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required.",
        )
    return

from app.database import SessionLocal
from app.models.user import User

async def require_user_admin(current_user: CurrentUser = Depends(get_current_user)):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user or not user.can_manage_users():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. User admin role required.",
            )
        return current_user
    finally:
        db.close()


async def require_data_admin(current_user: CurrentUser = Depends(get_current_user)):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user or not user.can_manage_data():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Data admin role required.",
            )
        return current_user
    finally:
        db.close()


async def require_super_admin(current_user: CurrentUser = Depends(get_current_user)):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user or not user.can_manage_system():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Super admin role required.",
            )
        return current_user
    finally:
        db.close()