from datetime import datetime
from typing import Optional

from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session

from app.models.info_object import InfoObject, Tag


class InfoObjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_all_paginated(
        self,
        page: int,
        size: int,
        sort: str = "id",
        direction: str = "asc",
        include_deleted: bool = False,
    ):
        query = self.db.query(InfoObject)

        if not include_deleted:
            query = query.filter(
                or_(
                    InfoObject.deletion_flag.is_(False),
                    InfoObject.deletion_flag.is_(None),
                )
            )

        return self._paginate(query, page, size, sort, direction)

    def find_deleted_paginated(
        self,
        page: int,
        size: int,
        sort: str = "deleted_at",
        direction: str = "desc",
    ):
        query = self.db.query(InfoObject).filter(InfoObject.deletion_flag.is_(True))
        return self._paginate(query, page, size, sort, direction)

    def find_my_paginated(
        self,
        user_id: int,
        page: int,
        size: int,
        sort: str = "id",
        direction: str = "asc",
        include_deleted: bool = False,
    ):
        query = self.db.query(InfoObject).filter(InfoObject.created_by == user_id)

        if not include_deleted:
            query = query.filter(
                or_(
                    InfoObject.deletion_flag.is_(False),
                    InfoObject.deletion_flag.is_(None),
                )
            )

        return self._paginate(query, page, size, sort, direction)

    def search(
        self,
        *,
        search_everywhere=None,
        title=None,
        text=None,
        author=None,
        source=None,
        publication_title=None,
        url=None,
        doi=None,
        tags=None,
        tag_mode="AND",
        publication_date_from=None,
        publication_date_to=None,
        include_deleted=False,
        page=0,
        size=20,
        sort="id",
        direction="asc",
    ):
        query = self.db.query(InfoObject)

        if search_everywhere:
            pattern = f"%{search_everywhere}%"
            query = query.filter(
                or_(
                    InfoObject.title.ilike(pattern),
                    InfoObject.content.ilike(pattern),
                    InfoObject.author.ilike(pattern),
                    InfoObject.source.ilike(pattern),
                    InfoObject.publication_title.ilike(pattern),
                    InfoObject.url.ilike(pattern),
                    InfoObject.doi.ilike(pattern),
                )
            )

        if title:
            query = query.filter(InfoObject.title.ilike(f"%{title}%"))
        if text:
            query = query.filter(InfoObject.content.ilike(f"%{text}%"))
        if author:
            query = query.filter(InfoObject.author.ilike(f"%{author}%"))
        if source:
            query = query.filter(InfoObject.source.ilike(f"%{source}%"))
        if publication_title:
            query = query.filter(InfoObject.publication_title.ilike(f"%{publication_title}%"))
        if url:
            query = query.filter(InfoObject.url.ilike(f"%{url}%"))
        if doi:
            query = query.filter(InfoObject.doi.ilike(f"%{doi}%"))

        if tags:
            if tag_mode.upper() == "OR":
                query = query.filter(InfoObject.tags.any(Tag.name.in_(tags)))
            else:
                for tag_name in tags:
                    query = query.filter(InfoObject.tags.any(Tag.name == tag_name))

        object_start = func.coalesce(InfoObject.publication_date_from, InfoObject.publication_date_to)
        object_end = func.coalesce(InfoObject.publication_date_to, InfoObject.publication_date_from)

        if publication_date_from is not None:
            query = query.filter(object_end >= publication_date_from)

        if publication_date_to is not None:
            query = query.filter(object_start <= publication_date_to)

        if not include_deleted:
            query = query.filter(
                or_(
                    InfoObject.deletion_flag.is_(False),
                    InfoObject.deletion_flag.is_(None),
                )
            )

        return self._paginate(query, page, size, sort, direction)

    def find_by_id(self, info_object_id: int) -> Optional[InfoObject]:
        return self.db.query(InfoObject).filter(InfoObject.id == info_object_id).first()

    def exists_by_id(self, info_object_id: int) -> bool:
        return self.find_by_id(info_object_id) is not None

    def save(self, info_object: InfoObject) -> InfoObject:
        self.db.add(info_object)
        self.db.commit()
        self.db.refresh(info_object)
        return info_object

    def delete_by_id(self, info_object_id: int) -> None:
        obj = self.find_by_id(info_object_id)
        if obj:
            self.db.delete(obj)
            self.db.commit()

    def find_deleted_older_than(self, cutoff: datetime):
        return (
            self.db.query(InfoObject)
            .filter(
                InfoObject.deletion_flag.is_(True),
                InfoObject.deleted_at.is_not(None),
                InfoObject.deleted_at < cutoff,
            )
            .all()
        )

    def _paginate(self, query, page: int, size: int, sort: str, direction: str):
        sort_field = getattr(InfoObject, sort, InfoObject.id)
        order_clause = asc(sort_field) if direction.lower() == "asc" else desc(sort_field)
        query = query.order_by(order_clause)

        total = query.count()
        items = query.offset(page * size).limit(size).all()
        pages = (total + size - 1) // size if total else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
        }