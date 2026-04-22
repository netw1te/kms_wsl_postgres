from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class InfoObjectDeletionRequest(Base):
    __tablename__ = "info_object_deletion_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)

    info_object_id = Column(
        Integer,
        ForeignKey("information_objects.info_id"),
        nullable=False,
    )

    requested_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    reason = Column(Text, nullable=True)

    replacement_info_object_id = Column(
        Integer,
        ForeignKey("information_objects.info_id"),
        nullable=True,
    )

    status = Column(String(30), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    reviewed_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    reviewed_at = Column(DateTime, nullable=True)