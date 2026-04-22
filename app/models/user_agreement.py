from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class UserAgreement(Base):
    __tablename__ = "user_agreements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    full_name = Column(String(50), nullable=False)
    job_title = Column(String(50), nullable=False)
    organization = Column(String(50), nullable=False)

    accepted_rules = Column(Boolean, nullable=False, default=False)
    accepted_personal_data = Column(Boolean, nullable=False, default=False)

    accepted_at = Column(DateTime, nullable=False, server_default=func.now())
    accepted_ip = Column(String(100), nullable=True)