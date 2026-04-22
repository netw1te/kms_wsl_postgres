import secrets
from functools import wraps
from typing import Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.user_repository import UserRepository


security = HTTPBasic()
pwd_context = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')


class MyUserDetails:
    def __init__(self, user):
        self.user = user

    @property
    def id(self) -> int:
        return self.user.id

    @property
    def login(self) -> str:
        return self.user.login

    @property
    def role(self) -> str:
        return self.user.role

    @property
    def full_name(self) -> Optional[str]:
        return self.user.full_name

    @property
    def email(self) -> Optional[str]:
        return self.user.email

    @property
    def authorities(self) -> list[str]:
        return [item.strip() for item in self.user.role.split(',') if item.strip()]

    def get_password(self) -> str:
        return self.user.password


class BCryptPasswordEncoder:
    def encode(self, raw_password: str) -> str:
        return pwd_context.hash(raw_password)

    def verify(self, raw_password: str, encoded_password: str) -> bool:
        return pwd_context.verify(raw_password, encoded_password)


password_encoder = BCryptPasswordEncoder()


async def get_current_user(
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> MyUserDetails:
    repo = UserRepository(db)
    user = repo.find_user_by_login(credentials.username)

    correct_username = secrets.compare_digest(credentials.username, user.login) if user else False
    correct_password = password_encoder.verify(credentials.password, user.password) if user else False

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Basic'},
        )

    return MyUserDetails(user)


def require_admin(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args, **kwargs):
        current_user = kwargs.get('current_user')
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')
        if 'ROLE_ADMIN' not in current_user.authorities:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied. Admin role required.')
        return await func(*args, **kwargs)

    return wrapper
