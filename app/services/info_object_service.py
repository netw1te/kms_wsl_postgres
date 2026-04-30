from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app.models.info_object import InfoObject, Tag
from app.models.info_object_attachment import InfoObjectAttachment
from app.models.info_object_deletion_request import InfoObjectDeletionRequest
from app.models.media_file import MediaFile
from app.repositories.info_object_repository import InfoObjectRepository


class InfoObjectService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = InfoObjectRepository(db)

    def _active_filter(self):
        return or_(
            InfoObject.deletion_flag.is_(False),
            InfoObject.deletion_flag.is_(None),
        )

    def _paginate(self, query, page: int, size: int, sort: str, direction: str):
        sort_column = getattr(InfoObject, sort, InfoObject.id)

        total = query.count()

        if direction.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        items = query.offset(page * size).limit(size).all()

        pages = 0
        if total > 0:
            pages = (total + size - 1) // size

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
        }

    def find_all(
        self,
        page: int = 0,
        size: int = 20,
        sort: str = "id",
        direction: str = "asc",
        include_deleted: bool = False,
    ):
        query = self.db.query(InfoObject)

        if not include_deleted:
            query = query.filter(self._active_filter())

        return self._paginate(
            query=query,
            page=page,
            size=size,
            sort=sort,
            direction=direction,
        )

    def find_deleted(
        self,
        page: int = 0,
        size: int = 20,
        sort: str = "deleted_at",
        direction: str = "desc",
    ):
        query = self.db.query(InfoObject).filter(
            InfoObject.deletion_flag.is_(True)
        )

        return self._paginate(
            query=query,
            page=page,
            size=size,
            sort=sort,
            direction=direction,
        )

    def find_my(
        self,
        user_id: int,
        page: int = 0,
        size: int = 20,
        sort: str = "id",
        direction: str = "asc",
        include_deleted: bool = False,
    ):
        query = self.db.query(InfoObject).filter(
            InfoObject.created_by == user_id
        )

        if not include_deleted:
            query = query.filter(self._active_filter())

        return self._paginate(
            query=query,
            page=page,
            size=size,
            sort=sort,
            direction=direction,
        )

    def find_by_id(self, info_object_id: int) -> Optional[InfoObject]:
        return self.repository.find_by_id(info_object_id)

    def exists_by_id(self, info_object_id: int) -> bool:
        return self.repository.exists_by_id(info_object_id)

    def save(self, info_object: InfoObject) -> InfoObject:
        return self.repository.save(info_object)

    def delete_by_id(self, info_object_id: int) -> None:
        self.repository.delete_by_id(info_object_id)

    def get_or_create_tags(self, tag_names: list[str]) -> list[Tag]:
        result = []

        for tag_name in tag_names:
            clean_name = tag_name.strip()

            if not clean_name:
                continue

            tag = self.db.query(Tag).filter(Tag.name == clean_name).first()

            if tag is None:
                tag = Tag(name=clean_name)
                self.db.add(tag)
                self.db.flush()

            result.append(tag)

        return result

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
        if tags:
            existing_tags = {
                row[0]
                for row in self.db.query(Tag.name).filter(Tag.name.in_(tags)).all()
            }

            missing_tags = [tag for tag in tags if tag not in existing_tags]

            if missing_tags:
                missing_text = ", ".join(missing_tags)
                raise ValueError(
                    f"Таких меток нет: {missing_text}. "
                    f"Удалите их из поиска или вернитесь к форме поиска."
                )

        query = self.db.query(InfoObject)

        if not include_deleted:
            query = query.filter(self._active_filter())

        if search_everywhere:
            pattern = f"%{search_everywhere.strip()}%"
            query = query.filter(
                or_(
                    InfoObject.title.ilike(pattern),
                    InfoObject.content.ilike(pattern),
                    InfoObject.author.ilike(pattern),
                    InfoObject.source.ilike(pattern),
                    InfoObject.publication_title.ilike(pattern),
                    InfoObject.url.ilike(pattern),
                    InfoObject.doi.ilike(pattern),
                    InfoObject.tags.any(Tag.name.ilike(pattern)),
                )
            )

        if title:
            query = query.filter(InfoObject.title.ilike(f"%{title.strip()}%"))

        if text:
            query = query.filter(InfoObject.content.ilike(f"%{text.strip()}%"))

        if author:
            query = query.filter(InfoObject.author.ilike(f"%{author.strip()}%"))

        if source:
            query = query.filter(InfoObject.source.ilike(f"%{source.strip()}%"))

        if publication_title:
            query = query.filter(
                InfoObject.publication_title.ilike(f"%{publication_title.strip()}%")
            )

        if url:
            query = query.filter(InfoObject.url.ilike(f"%{url.strip()}%"))

        if doi:
            query = query.filter(InfoObject.doi.ilike(f"%{doi.strip()}%"))

        if publication_date_from:
            query = query.filter(
                InfoObject.publication_date_from >= publication_date_from
            )

        if publication_date_to:
            query = query.filter(
                InfoObject.publication_date_to <= publication_date_to
            )

        if tags:
            if tag_mode == "AND":
                for tag in tags:
                    query = query.filter(InfoObject.tags.any(Tag.name == tag))
            else:
                query = query.filter(InfoObject.tags.any(Tag.name.in_(tags)))

        return self._paginate(
            query=query,
            page=page,
            size=size,
            sort=sort,
            direction=direction,
        )

    def restore_info_object(self, info_object_id: int) -> Optional[InfoObject]:
        info_object = self.repository.find_by_id(info_object_id)

        if info_object is None:
            return None

        info_object.deletion_flag = False
        info_object.deletion_reason = None
        info_object.deleted_by = None
        info_object.deleted_at = None
        info_object.replacement_info_object_id = None

        return self.repository.save(info_object)

    def mark_deleted(
        self,
        info_object_id: int,
        *,
        reason: str | None,
        deleted_by: int | None,
        replacement_info_object_id: int | None = None,
    ) -> Optional[InfoObject]:
        info_object = self.repository.find_by_id(info_object_id)

        if info_object is None:
            return None

        info_object.deletion_flag = True
        info_object.deletion_reason = reason
        info_object.deleted_by = deleted_by
        info_object.deleted_at = datetime.utcnow()
        info_object.replacement_info_object_id = replacement_info_object_id

        return self.repository.save(info_object)

    def hard_delete_info_object(self, info_object_id: int) -> bool:
        info_object = self.repository.find_by_id(info_object_id)

        if info_object is None:
            return False

        (
            self.db.query(InfoObject)
            .filter(InfoObject.replacement_info_object_id == info_object_id)
            .update(
                {InfoObject.replacement_info_object_id: None},
                synchronize_session=False,
            )
        )

        (
            self.db.query(InfoObjectDeletionRequest)
            .filter(
                InfoObjectDeletionRequest.replacement_info_object_id
                == info_object_id
            )
            .update(
                {InfoObjectDeletionRequest.replacement_info_object_id: None},
                synchronize_session=False,
            )
        )

        attachment_rows = (
            self.db.query(InfoObjectAttachment)
            .filter(InfoObjectAttachment.info_object_id == info_object_id)
            .all()
        )

        media_file_ids = [row.media_file_id for row in attachment_rows]

        (
            self.db.query(InfoObjectAttachment)
            .filter(InfoObjectAttachment.info_object_id == info_object_id)
            .delete(synchronize_session=False)
        )

        (
            self.db.query(InfoObjectDeletionRequest)
            .filter(InfoObjectDeletionRequest.info_object_id == info_object_id)
            .delete(synchronize_session=False)
        )

        for media_file_id in media_file_ids:
            remaining_links = (
                self.db.query(InfoObjectAttachment)
                .filter(InfoObjectAttachment.media_file_id == media_file_id)
                .count()
            )

            if remaining_links == 0:
                media_file = (
                    self.db.query(MediaFile)
                    .filter(MediaFile.id == media_file_id)
                    .first()
                )

                if media_file:
                    file_path = Path(media_file.file_path)

                    if file_path.exists():
                        file_path.unlink()

                    self.db.delete(media_file)

        self.db.delete(info_object)
        self.db.commit()

        return True

    def purge_deleted_older_than(self, days: int = 7) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        expired = self.repository.find_deleted_older_than(cutoff)
        deleted_count = 0

        for item in expired:
            if self.hard_delete_info_object(item.id):
                deleted_count += 1

        return deleted_count