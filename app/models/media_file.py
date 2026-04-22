from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False)
    file_path = Column(String(1000), nullable=False, unique=True)
    content_type = Column(String(255), nullable=True)
    size_bytes = Column(Integer, nullable=False)
    checksum_sha256 = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)