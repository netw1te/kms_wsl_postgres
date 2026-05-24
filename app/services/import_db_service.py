import json
import zipfile
from datetime import datetime
from io import BytesIO
from typing import Any

from sqlalchemy.orm import Session

from app.auth import PasswordEncoder
from app.models.info_object import InfoObject, Tag
from app.models.user import User
from app.models.user_agreement import UserAgreement
from app.models.search_query import SearchQuery
from app.models.info_object_deletion_request import InfoObjectDeletionRequest
from app.models.media_file import MediaFile
from app.models.info_object_attachment import InfoObjectAttachment


class ImportDBService:
    def __init__(self, db: Session):
        self.db = db

    def _parse_datetime(self, value: Any):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    def _read_json_files(self, zip_bytes: bytes) -> dict[str, Any]:
        result: dict[str, Any] = {}

        with zipfile.ZipFile(BytesIO(zip_bytes), "r") as archive:
            for name in archive.namelist():
                if not name.endswith(".json"):
                    continue

                filename = name.split("/")[-1]
                with archive.open(name) as file:
                    result[filename] = json.loads(file.read().decode("utf-8"))

        return result

    def _upsert_users(self, rows: list[dict[str, Any]]) -> tuple[int, dict[int, User], dict[str, User]]:
        count = 0
        users_by_old_id: dict[int, User] = {}
        users_by_login: dict[str, User] = {}

        for row in rows:
            login = row.get("login")
            if not login:
                continue

            old_id = row.get("id")

            user = self.db.query(User).filter(User.login == login).first()

            if user is None and old_id is not None:
                user = self.db.query(User).filter(User.id == int(old_id)).first()

            if user is None:
                if old_id is not None:
                    user = User(id=int(old_id), login=login)
                else:
                    user = User(login=login)
                self.db.add(user)

            user.login = login

            incoming_password = row.get("password")
            if incoming_password:
                user.password = incoming_password
            elif not getattr(user, "password", None):
                user.password = PasswordEncoder.hash("user123")

            user.full_name = row.get("full_name")
            user.email = row.get("email")
            user.access_start = self._parse_datetime(row.get("access_start"))
            user.access_end = self._parse_datetime(row.get("access_end"))
            user.is_user_admin = bool(row.get("is_user_admin", False))
            user.is_data_admin = bool(row.get("is_data_admin", False))
            user.is_super_admin = bool(row.get("is_super_admin", False))

            self.db.flush()

            if old_id is not None:
                users_by_old_id[int(old_id)] = user
            users_by_login[login] = user
            count += 1

        return count, users_by_old_id, users_by_login

    def _upsert_tags(self, rows: list[dict[str, Any]]) -> dict[int, Tag]:
        tag_by_old_id: dict[int, Tag] = {}

        for row in rows:
            name = row.get("name")
            if not name:
                continue

            tag = self.db.query(Tag).filter(Tag.name == name).first()
            if tag is None:
                tag = Tag(name=name)
                self.db.add(tag)
                self.db.flush()

            old_id = row.get("id")
            if old_id is not None:
                tag_by_old_id[int(old_id)] = tag

        return tag_by_old_id

    def _upsert_info_objects(self, rows: list[dict[str, Any]]) -> dict[int, InfoObject]:
        object_by_old_id: dict[int, InfoObject] = {}

        for row in rows:
            old_id = row.get("id")
            if old_id is None:
                continue

            obj = self.db.query(InfoObject).filter(InfoObject.id == int(old_id)).first()
            if obj is None:
                obj = InfoObject(id=int(old_id))
                self.db.add(obj)

            obj.title = row.get("title")
            obj.content = row.get("content")
            obj.source = row.get("source")
            obj.author = row.get("author")
            obj.url = row.get("url")
            obj.doi = row.get("doi")
            obj.publication_title = row.get("publication_title")

            obj.publication_date_from_raw = row.get("publication_date_from_raw")
            obj.publication_date_to_raw = row.get("publication_date_to_raw")
            obj.publication_date_from = self._parse_datetime(row.get("publication_date_from"))
            obj.publication_date_to = self._parse_datetime(row.get("publication_date_to"))

            if hasattr(obj, "publication_date_raw"):
                obj.publication_date_raw = (
                    row.get("publication_date_raw")
                    or row.get("publication_date_from_raw")
                    or ""
                )

            if hasattr(obj, "publication_date"):
                obj.publication_date = (
                    self._parse_datetime(row.get("publication_date"))
                    or obj.publication_date_from
                    or datetime.utcnow()
                )

            obj.created_at = self._parse_datetime(row.get("created_at")) or datetime.utcnow()
            obj.updated_at = self._parse_datetime(row.get("updated_at")) or datetime.utcnow()
            obj.created_by = row.get("created_by")

            obj.deletion_flag = bool(row.get("deletion_flag", False))
            obj.deletion_reason = row.get("deletion_reason")
            obj.deleted_by = row.get("deleted_by")
            obj.deleted_at = self._parse_datetime(row.get("deleted_at"))
            obj.replacement_info_object_id = row.get("replacement_info_object_id")

            self.db.flush()
            object_by_old_id[int(old_id)] = obj

        return object_by_old_id

    def _attach_tags_from_rows(
        self,
        info_rows: list[dict[str, Any]],
        object_by_old_id: dict[int, InfoObject],
    ) -> int:
        count = 0

        for row in info_rows:
            old_id = row.get("id")
            if old_id is None or int(old_id) not in object_by_old_id:
                continue

            tag_names = row.get("tags") or []
            tags = []

            for name in tag_names:
                if not name:
                    continue

                tag = self.db.query(Tag).filter(Tag.name == name).first()
                if tag is None:
                    tag = Tag(name=name)
                    self.db.add(tag)
                    self.db.flush()

                tags.append(tag)

            object_by_old_id[int(old_id)].tags = tags
            count += len(tags)

        return count

    def _import_user_agreements(self, rows: list[dict[str, Any]]) -> int:
        count = 0

        for row in rows:
            old_id = row.get("id")
            if old_id is None:
                continue

            item = self.db.query(UserAgreement).filter(UserAgreement.id == int(old_id)).first()
            if item is None:
                item = UserAgreement(id=int(old_id))
                self.db.add(item)

            item.user_id = row.get("user_id")
            item.full_name = row.get("full_name") or ""
            item.job_title = row.get("job_title") or ""
            item.organization = row.get("organization") or ""
            item.accepted_rules = bool(row.get("accepted_rules", False))
            item.accepted_personal_data = bool(row.get("accepted_personal_data", False))
            item.accepted_at = self._parse_datetime(row.get("accepted_at")) or datetime.utcnow()
            item.accepted_ip = row.get("accepted_ip")

            count += 1

        return count

    def _import_user_export_agreement(self, row: dict[str, Any] | None, user_id: int | None) -> int:
        if not row or not user_id:
            return 0

        item = (
            self.db.query(UserAgreement)
            .filter(UserAgreement.user_id == user_id)
            .first()
        )

        if item is None:
            item = UserAgreement(user_id=user_id)
            self.db.add(item)

        item.full_name = row.get("full_name") or ""
        item.job_title = row.get("job_title") or ""
        item.organization = row.get("organization") or ""
        item.accepted_rules = True
        item.accepted_personal_data = True
        item.accepted_at = self._parse_datetime(row.get("accepted_at")) or datetime.utcnow()
        item.accepted_ip = row.get("accepted_ip")

        return 1

    def _import_search_queries(self, rows: list[dict[str, Any]]) -> int:
        count = 0

        for row in rows:
            old_id = row.get("id")
            if old_id is None:
                continue

            item = self.db.query(SearchQuery).filter(SearchQuery.id == int(old_id)).first()
            if item is None:
                item = SearchQuery(id=int(old_id))
                self.db.add(item)

            item.created_at = self._parse_datetime(row.get("created_at")) or datetime.utcnow()
            item.name = row.get("name") or "Импортированный запрос"
            item.search_everywhere = row.get("search_everywhere")
            item.title = row.get("title")
            item.text = row.get("text")
            item.source = row.get("source")
            item.author = row.get("author")
            item.publication_title = row.get("publication_title")
            item.url = row.get("url")
            item.doi = row.get("doi")
            item.tags_text = row.get("tags_text")
            item.tag_mode = row.get("tag_mode") or "AND"
            item.created_after_raw = row.get("created_after_raw")
            item.created_before_raw = row.get("created_before_raw")
            item.info_object_id = row.get("info_object_id")
            item.user_id = row.get("user_id")

            count += 1

        return count

    def _import_deletion_requests(self, rows: list[dict[str, Any]]) -> int:
        count = 0

        for row in rows:
            old_id = row.get("id")
            if old_id is None:
                continue

            item = (
                self.db.query(InfoObjectDeletionRequest)
                .filter(InfoObjectDeletionRequest.id == int(old_id))
                .first()
            )

            if item is None:
                item = InfoObjectDeletionRequest(id=int(old_id))
                self.db.add(item)

            item.info_object_id = row.get("info_object_id")
            item.requested_by = row.get("requested_by")
            item.reason = row.get("reason")
            item.replacement_info_object_id = row.get("replacement_info_object_id")
            item.status = row.get("status") or "pending"
            item.created_at = self._parse_datetime(row.get("created_at")) or datetime.utcnow()
            item.reviewed_by = row.get("reviewed_by")
            item.reviewed_at = self._parse_datetime(row.get("reviewed_at"))

            count += 1

        return count

    def _import_media_files(self, rows: list[dict[str, Any]]) -> int:
        count = 0

        for row in rows:
            old_id = row.get("id")
            if old_id is None:
                continue

            item = self.db.query(MediaFile).filter(MediaFile.id == int(old_id)).first()
            if item is None:
                item = MediaFile(id=int(old_id))
                self.db.add(item)

            item.original_name = row.get("original_name") or ""
            item.stored_name = row.get("stored_name") or ""
            item.file_path = row.get("file_path") or ""
            item.content_type = row.get("content_type")
            item.size_bytes = int(row.get("size_bytes") or 0)
            item.checksum_sha256 = row.get("checksum_sha256") or ""
            item.created_at = self._parse_datetime(row.get("created_at")) or datetime.utcnow()
            item.uploaded_by = row.get("uploaded_by")

            count += 1

        return count

    def _import_attachments(self, rows: list[dict[str, Any]]) -> int:
        count = 0

        for row in rows:
            old_id = row.get("id")
            if old_id is None:
                continue

            item = (
                self.db.query(InfoObjectAttachment)
                .filter(InfoObjectAttachment.id == int(old_id))
                .first()
            )

            if item is None:
                item = InfoObjectAttachment(id=int(old_id))
                self.db.add(item)

            item.info_object_id = row.get("info_object_id")
            item.media_file_id = row.get("media_file_id")
            item.created_at = self._parse_datetime(row.get("created_at")) or datetime.utcnow()

            count += 1

        return count

    def _find_user_export_parts(self, data: dict[str, Any]):
        user_file = None
        objects_file = None
        queries_file = None
        agreement_file = None

        for filename in data.keys():
            if not filename.startswith("user_"):
                continue

            if filename.endswith("_objects.json"):
                objects_file = filename
            elif filename.endswith("_queries.json"):
                queries_file = filename
            elif filename.endswith("_agreement.json"):
                agreement_file = filename
            elif filename.endswith(".json"):
                user_file = filename

        if not user_file or not objects_file:
            return None

        return {
            "user": data.get(user_file),
            "objects": data.get(objects_file) or [],
            "queries": data.get(queries_file) or [],
            "agreement": data.get(agreement_file),
        }

    def _import_user_export(self, parts: dict[str, Any]) -> dict[str, int]:
        user_row = parts["user"]
        object_rows = parts["objects"]
        query_rows = parts["queries"]
        agreement_row = parts["agreement"]

        if not isinstance(user_row, dict):
            raise ValueError("Некорректный файл пользователя в ZIP.")

        if not isinstance(object_rows, list):
            raise ValueError("Некорректный файл объектов пользователя в ZIP.")

        if not isinstance(query_rows, list):
            query_rows = []

        users_count, _, users_by_login = self._upsert_users([user_row])

        login = user_row.get("login")
        user = users_by_login.get(login) if login else None
        user_id = user.id if user else user_row.get("id")

        normalized_objects = []
        for row in object_rows:
            if not isinstance(row, dict):
                continue

            normalized = dict(row)
            normalized["created_by"] = user_id
            normalized["updated_at"] = normalized.get("updated_at") or datetime.utcnow().isoformat()
            normalized["deletion_flag"] = bool(normalized.get("deletion_flag", False))

            normalized_objects.append(normalized)

        objects_by_old_id = self._upsert_info_objects(normalized_objects)
        tag_links_count = self._attach_tags_from_rows(normalized_objects, objects_by_old_id)

        normalized_queries = []
        for row in query_rows:
            if not isinstance(row, dict):
                continue

            normalized = dict(row)
            normalized["user_id"] = user_id
            normalized_queries.append(normalized)

        queries_count = self._import_search_queries(normalized_queries)
        agreement_count = self._import_user_export_agreement(agreement_row, user_id)

        return {
            "users": users_count,
            "tags": 0,
            "info_objects": len(objects_by_old_id),
            "tag_links": tag_links_count,
            "user_agreements": agreement_count,
            "search_queries": queries_count,
            "deletion_requests": 0,
            "media_files": 0,
            "attachments": 0,
        }

    def import_zip(self, zip_bytes: bytes) -> dict[str, int]:
        data = self._read_json_files(zip_bytes)

        user_export_parts = self._find_user_export_parts(data)
        if user_export_parts is not None:
            result = self._import_user_export(user_export_parts)
            self.db.commit()
            return result

        users_count, _, _ = self._upsert_users(data.get("users.json", []))
        tags_by_old_id = self._upsert_tags(data.get("tags.json", []))
        objects_by_old_id = self._upsert_info_objects(data.get("info_objects.json", []))

        tag_links_count = self._attach_tags_from_rows(
            data.get("info_objects.json", []),
            objects_by_old_id,
        )

        agreements_count = self._import_user_agreements(data.get("user_agreements.json", []))
        queries_count = self._import_search_queries(data.get("search_queries.json", []))
        deletion_requests_count = self._import_deletion_requests(data.get("deletion_requests.json", []))
        media_files_count = self._import_media_files(data.get("media_files.json", []))
        attachments_count = self._import_attachments(data.get("info_object_attachments.json", []))

        self.db.commit()

        return {
            "users": users_count,
            "tags": len(tags_by_old_id),
            "info_objects": len(objects_by_old_id),
            "tag_links": tag_links_count,
            "user_agreements": agreements_count,
            "search_queries": queries_count,
            "deletion_requests": deletion_requests_count,
            "media_files": media_files_count,
            "attachments": attachments_count,
        }