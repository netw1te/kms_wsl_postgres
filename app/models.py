from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import relationship

from app.db import Base


information_objects_tags = Table(
    "information_objects_tags",
    Base.metadata,
    Column("info_id", Integer, ForeignKey("information_objects.info_id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column("user_id", Integer, primary_key=True, autoincrement=True)
    login = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    email = Column(String(255))
    role = Column(String(50), nullable=False, default="ROLE_USER")


class InfoObject(Base):
    __tablename__ = "information_objects"

    id = Column("info_id", Integer, primary_key=True, autoincrement=True)
    title = Column(String(255))
    content = Column(Text)
    source = Column(String(255))
    author = Column(String(100))
    url = Column(String(500))
    doi = Column(String(100))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    deletion_flag = Column(Boolean, default=False, nullable=False)
    deletion_reason = Column(String(500))

    tags = relationship("Tag", secondary=information_objects_tags, back_populates="info_objects")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    info_objects = relationship("InfoObject", secondary=information_objects_tags, back_populates="tags")
