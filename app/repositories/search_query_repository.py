from typing import Optional

from sqlalchemy.orm import Session

from app.models.search_query import SearchQuery


class SearchQueryRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, search_query: SearchQuery) -> SearchQuery:
        if search_query.id:
            existing = self.find_by_id(search_query.id)
            if existing:
                for key, value in search_query.__dict__.items():
                    if key not in {"_sa_instance_state"}:
                        setattr(existing, key, value)
                self.db.commit()
                self.db.refresh(existing)
                return existing

        self.db.add(search_query)
        self.db.commit()
        self.db.refresh(search_query)
        return search_query

    def find_by_id(self, search_query_id: int) -> Optional[SearchQuery]:
        return (
            self.db.query(SearchQuery)
            .filter(SearchQuery.id == search_query_id)
            .first()
        )

    def find_by_user_id(self, user_id: int, skip: int = 0, limit: int = 100):
        query = (
            self.db.query(SearchQuery)
            .filter(SearchQuery.user_id == user_id)
            .order_by(SearchQuery.created_at.desc())
        )
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return {"items": items, "total": total}

    def delete(self, search_query: SearchQuery):
        self.db.delete(search_query)
        self.db.commit()