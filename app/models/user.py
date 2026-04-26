from sqlalchemy import Column, Integer, String
from app.database import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, default='ROLE_USER')
    def is_admin(self) -> bool:
        return self.role == "ROLE_ADMIN"