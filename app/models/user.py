from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)

    role = Column(String(50), nullable=False, default="ROLE_USER")

    access_start = Column(Date, nullable=True)
    access_end = Column(Date, nullable=True)

    is_user_admin = Column(Boolean, nullable=False, default=False)
    is_data_admin = Column(Boolean, nullable=False, default=False)
    is_super_admin = Column(Boolean, nullable=False, default=False)

    organization = Column(String(255), nullable=True)
    position = Column(String(255), nullable=True)
    rules_accepted_at = Column(DateTime(timezone=True), nullable=True)
    registration_ip = Column(String(45), nullable=True)
    phone = Column(String(20), nullable=True)
    comment = Column(String(200), nullable=True)

    def can_manage_users(self) -> bool:
        return bool(self.is_user_admin or self.is_super_admin)

    def can_manage_data(self) -> bool:
        return bool(self.is_data_admin or self.is_super_admin)

    def can_manage_system(self) -> bool:
        return bool(self.is_super_admin)

    def is_admin(self) -> bool:
        return bool(
            self.role == "ROLE_ADMIN"
            or self.is_user_admin
            or self.is_data_admin
            or self.is_super_admin
        )