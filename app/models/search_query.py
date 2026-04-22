from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class SearchQuery(Base):
    __tablename__ = "search_queries"

    id = Column(Integer, primary_key=True, autoincrement=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    name = Column(String(200), nullable=False)

    search_everywhere = Column(String, nullable=True)
    title = Column(String(255), nullable=True)
    text = Column(String, nullable=True)
    source = Column(String(500), nullable=True)
    author = Column(String(255), nullable=True)
    publication_title = Column(String(500), nullable=True)
    url = Column(String(500), nullable=True)
    doi = Column(String(255), nullable=True)

    tags_text = Column(String, nullable=True)
    tag_mode = Column(String(10), nullable=True, default="AND")

    created_after_raw = Column(String(20), nullable=True)
    created_before_raw = Column(String(20), nullable=True)

    info_object_id = Column(Integer, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)