from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


information_objects_tags = Table(
    "information_objects_tags",
    Base.metadata,
    Column(
        "info_id",
        Integer,
        ForeignKey("information_objects.info_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class InfoObject(Base):
    __tablename__ = "information_objects"

    id = Column("info_id", Integer, primary_key=True, autoincrement=True)

    title = Column(String(255))
    content = Column(Text)
    source = Column(String(500))
    url = Column(String(500))
    author = Column(String(255))
    doi = Column(String(255))

    publication_title = Column(String(500))

    publication_date_from_raw = Column(String(20))
    publication_date_to_raw = Column(String(20))
    publication_date_from = Column(DateTime, nullable=True)
    publication_date_to = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    created_by = Column(Integer, nullable=True)

    deletion_flag = Column(Boolean, default=False, nullable=False)
    deletion_reason = Column(String(500))
    deleted_by = Column(Integer, nullable=True)

    replacement_info_object_id = Column(
        Integer,
        ForeignKey("information_objects.info_id"),
        nullable=True,
    )

    tags = relationship(
        "Tag",
        secondary=information_objects_tags,
        back_populates="info_objects",
    )


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)

    info_objects = relationship(
        "InfoObject",
        secondary=information_objects_tags,
        back_populates="tags",
    )