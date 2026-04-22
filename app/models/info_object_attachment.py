from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class InfoObjectAttachment(Base):
    __tablename__ = "info_object_attachments"
    __table_args__ = (
        UniqueConstraint("info_object_id", "media_file_id", name="uq_info_object_attachment"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    info_object_id = Column(
        Integer,
        ForeignKey("information_objects.info_id", ondelete="CASCADE"),
        nullable=False,
    )
    media_file_id = Column(
        Integer,
        ForeignKey("media_files.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())