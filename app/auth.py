from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User


security = HTTPBasic()
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


def authenticate_user(db: Session, username: str, password: str) -> CurrentUser | None:
    user = db.query(User).filter(User.login == username).first()
    if user is None:
        return None
    if not PasswordEncoder.verify(password, user.password):
        return None

    return CurrentUser(
        id=user.id,
        login=user.login,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
    )


async def get_current_user(
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> CurrentUser:
    user = authenticate_user(db, credentials.username, credentials.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user


async def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required.",
        )
    return current_user