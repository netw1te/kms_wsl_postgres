from typing import Optional

from sqlalchemy.orm import Session

from app.models.info_object import InfoObject, Tag
from app.repositories.info_object_repository import InfoObjectRepository


class InfoObjectService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = InfoObjectRepository(db)

    def find_all(self, page: int = 0, size: int = 20, sort: str = "id", direction: str = "asc"):
        return self.repository.find_all_paginated(page=page, size=size, sort=sort, direction=direction)

    def find_my(
        self,
        user_id: int,
        page: int = 0,
        size: int = 20,
        sort: str = "id",
        direction: str = "asc",
        include_deleted: bool = True,
    ):
        return self.repository.find_my_paginated(
            user_id=user_id,
            page=page,
            size=size,
            sort=sort,
            direction=direction,
            include_deleted=include_deleted,
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
        title=None,
        text=None,
        author=None,
        source=None,
        publication_title=None,
        doi=None,
        tags=None,
        tag_mode="AND",
        include_deleted=False,
        page=0,
        size=20,
        sort="id",
        direction="asc",
    ):
        if tags:
            existing_tags = {
                row[0] for row in self.db.query(Tag.name).filter(Tag.name.in_(tags)).all()
            }
            missing_tags = [tag for tag in tags if tag not in existing_tags]
            if missing_tags:
                missing_text = ", ".join(missing_tags)
                raise ValueError(
                    f"Таких меток нет: {missing_text}. Удалите их из поиска или вернитесь к форме поиска."
                )

        return self.repository.search(
            title=title,
            text=text,
            author=author,
            source=source,
            publication_title=publication_title,
            doi=doi,
            tags=tags,
            tag_mode=tag_mode,
            include_deleted=include_deleted,
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
        info_object.replacement_info_object_id = None
        return self.repository.save(info_object)