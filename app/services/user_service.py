from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, db: Session):
        self.repository = UserRepository(db)

    # TODO Убрать костыль с проверкой на админа
    def is_admin_by_login(self, login: str) -> bool:
        user = self.repository.find_user_by_login(login)
        return bool(user and (user.is_user_admin or user.is_super_admin or user.is_data_admin))

    def is_admin_by_id(self, user_id: int) -> bool:
        user = self.repository.find_by_id(user_id)
        return bool(user and (user.is_user_admin or user.is_super_admin or user.is_data_admin))

    def get_info_by_login(self, login: str) -> Optional[User]:
        return self.repository.find_user_by_login(login)
