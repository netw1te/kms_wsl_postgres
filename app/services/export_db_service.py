import json
import zipfile
from io import BytesIO
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.info_object import InfoObject, Tag
from app.models.user import User
from app.models.user_agreement import UserAgreement
from app.models.search_query import SearchQuery
from app.models.info_object_deletion_request import InfoObjectDeletionRequest
from app.models.media_file import MediaFile
from app.models.info_object_attachment import InfoObjectAttachment
from app.models.captcha import Captcha


class ExportDBService:
    def __init__(self, db: Session):
        self.db = db

    def _serialize_row(self, row, columns):
        data = {}
        for col in columns:
            val = getattr(row, col, None)
            if hasattr(val, 'isoformat'):
                val = val.isoformat()
            data[col] = val
        return data

    def _table_to_json(self, model, columns, filename, timestamp):
        rows = self.db.query(model).all()
        data = [self._serialize_row(r, columns) for r in rows]
        return (f"{timestamp}/{filename}", json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))

    def export_all_databases(self) -> bytes:
        buffer = BytesIO()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            tables = [
                (InfoObject, ['id', 'title', 'content', 'source', 'author', 'url', 'doi',
                              'publication_title', 'publication_date_from_raw', 'publication_date_to_raw',
                              'publication_date_from', 'publication_date_to', 'created_at', 'updated_at',
                              'created_by', 'deletion_flag', 'deletion_reason', 'deleted_by',
                              'replacement_info_object_id'], 'info_objects.json'),
                (Tag, ['id', 'name'], 'tags.json'),
                (User, ['id', 'login', 'password', 'full_name', 'email', 'role'], 'users.json'),
                (UserAgreement, ['id', 'user_id', 'full_name', 'job_title', 'organization',
                                 'accepted_rules', 'accepted_personal_data', 'accepted_at', 'accepted_ip'], 'user_agreements.json'),
                (SearchQuery, ['id', 'created_at', 'name', 'search_everywhere', 'title', 'text',
                               'source', 'author', 'publication_title', 'url', 'doi', 'tags_text',
                               'tag_mode', 'created_after_raw', 'created_before_raw', 'info_object_id',
                               'user_id'], 'search_queries.json'),
                (InfoObjectDeletionRequest, ['id', 'info_object_id', 'requested_by', 'reason',
                                             'replacement_info_object_id', 'status', 'created_at',
                                             'reviewed_by', 'reviewed_at'], 'deletion_requests.json'),
                (MediaFile, ['id', 'original_name', 'stored_name', 'file_path', 'content_type',
                             'size_bytes', 'checksum_sha256', 'created_at', 'uploaded_by'], 'media_files.json'),
                (InfoObjectAttachment, ['id', 'info_object_id', 'media_file_id', 'created_at'], 'info_object_attachments.json'),
                (Captcha, ['id', 'session_id', 'text', 'created_at', 'expires_at', 'used'], 'captcha.json'),
            ]

            for model, columns, filename in tables:
                try:
                    path, content = self._table_to_json(model, columns, filename, timestamp)
                    zf.writestr(path, content)
                except Exception:
                    pass

        buffer.seek(0)
        return buffer.getvalue()

    def export_kms_databases(self) -> bytes:
        buffer = BytesIO()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            info_objects = self.db.query(InfoObject).all()
            io_data = []
            for obj in info_objects:
                io_data.append({
                    'id': obj.id,
                    'title': obj.title,
                    'content': obj.content,
                    'source': obj.source,
                    'author': obj.author,
                    'url': obj.url,
                    'doi': obj.doi,
                    'publication_title': obj.publication_title,
                    'publication_date_from_raw': obj.publication_date_from_raw,
                    'publication_date_to_raw': obj.publication_date_to_raw,
                    'publication_date_from': obj.publication_date_from.isoformat() if obj.publication_date_from else None,
                    'publication_date_to': obj.publication_date_to.isoformat() if obj.publication_date_to else None,
                    'created_at': obj.created_at.isoformat() if obj.created_at else None,
                    'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
                    'created_by': obj.created_by,
                    'deletion_flag': obj.deletion_flag,
                    'deletion_reason': obj.deletion_reason,
                    'deleted_by': obj.deleted_by,
                    'replacement_info_object_id': obj.replacement_info_object_id,
                    'tags': [tag.name for tag in obj.tags]
                })
            zf.writestr(f"{timestamp}/info_objects.json", json.dumps(io_data, ensure_ascii=False, indent=2).encode('utf-8'))

            tags = self.db.query(Tag).all()
            tags_data = [{'id': t.id, 'name': t.name} for t in tags]
            zf.writestr(f"{timestamp}/tags.json", json.dumps(tags_data, ensure_ascii=False, indent=2).encode('utf-8'))

        buffer.seek(0)
        return buffer.getvalue()

    def export_user_database(self, login: str) -> bytes:
        buffer = BytesIO()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        user = self.db.query(User).filter(User.login == login).first()

        if not user:
            return None

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            user_data = {
                'id': user.id,
                'login': user.login,
                'full_name': user.full_name,
                'email': user.email,
                'role': user.role,
                'exported_at': datetime.now().isoformat()
            }
            zf.writestr(f"{timestamp}/user_{login}.json", json.dumps(user_data, ensure_ascii=False, indent=2).encode('utf-8'))

            my_objects = self.db.query(InfoObject).filter(InfoObject.created_by == user.id).all()
            objects_data = []
            for obj in my_objects:
                objects_data.append({
                    'id': obj.id,
                    'title': obj.title,
                    'content': obj.content,
                    'source': obj.source,
                    'author': obj.author,
                    'url': obj.url,
                    'doi': obj.doi,
                    'publication_title': obj.publication_title,
                    'publication_date_from_raw': obj.publication_date_from_raw,
                    'publication_date_to_raw': obj.publication_date_to_raw,
                    'created_at': obj.created_at.isoformat() if obj.created_at else None,
                    'deletion_flag': obj.deletion_flag,
                    'tags': [tag.name for tag in obj.tags]
                })
            zf.writestr(f"{timestamp}/user_{login}_objects.json", json.dumps(objects_data, ensure_ascii=False, indent=2).encode('utf-8'))

            my_queries = self.db.query(SearchQuery).filter(SearchQuery.user_id == user.id).all()
            queries_data = [{'id': q.id, 'name': q.name, 'created_at': q.created_at.isoformat() if q.created_at else None} for q in my_queries]
            zf.writestr(f"{timestamp}/user_{login}_queries.json", json.dumps(queries_data, ensure_ascii=False, indent=2).encode('utf-8'))

            agreement = self.db.query(UserAgreement).filter(UserAgreement.user_id == user.id).first()
            if agreement:
                agreement_data = {
                    'full_name': agreement.full_name,
                    'job_title': agreement.job_title,
                    'organization': agreement.organization,
                    'accepted_at': agreement.accepted_at.isoformat() if agreement.accepted_at else None,
                    'accepted_ip': agreement.accepted_ip
                }
                zf.writestr(f"{timestamp}/user_{login}_agreement.json", json.dumps(agreement_data, ensure_ascii=False, indent=2).encode('utf-8'))

        buffer.seek(0)
        return buffer.getvalue()