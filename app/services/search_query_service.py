from typing import Optional

from sqlalchemy.orm import Session

from app.models.search_query import SearchQuery
from app.repositories.search_query_repository import SearchQueryRepository


class SearchQueryService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = SearchQueryRepository(db)

    def create(self, search_query: SearchQuery) -> SearchQuery:
        return self.repository.save(search_query)

    def get_by_id(self, search_query_id: int) -> Optional[SearchQuery]:
        return self.repository.find_by_id(search_query_id)

    def get_my_queries(self, user_id: int, skip: int = 0, limit: int = 100):
        return self.repository.find_by_user_id(user_id, skip, limit)

    def rename(self, search_query: SearchQuery, new_name: str) -> SearchQuery:
        search_query.name = new_name
        return self.repository.save(search_query)

    def delete(self, search_query: SearchQuery):
        self.repository.delete(search_query)