from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.database import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)

    access_start = Column(DateTime, nullable=True)
    access_end = Column(DateTime, nullable=True)

    is_user_admin = Column(Boolean, default=False)
    is_data_admin = Column(Boolean, default=False)
    is_super_admin = Column(Boolean, default=False)

    def can_manage_users(self) -> bool:
        return self.is_user_admin

    def can_manage_data(self) -> bool:
        return self.is_data_admin

    def can_manage_system(self) -> bool:
        return self.is_super_admin