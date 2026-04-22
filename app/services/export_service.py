from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.orm import Session

from app.models.info_object import InfoObject
from app.models.info_object_attachment import InfoObjectAttachment
from app.models.media_file import MediaFile


def _rtf_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\n", "\\par ")
    )


class ExportService:
    def __init__(self, db: Session):
        self.db = db

    def get_info_object_or_none(self, info_object_id: int):
        return self.db.query(InfoObject).filter(InfoObject.id == info_object_id).first()

    def get_files_for_info_object(self, info_object_id: int):
        return (
            self.db.query(MediaFile)
            .join(InfoObjectAttachment, InfoObjectAttachment.media_file_id == MediaFile.id)
            .filter(InfoObjectAttachment.info_object_id == info_object_id)
            .order_by(MediaFile.id.asc())
            .all()
        )

    def build_rtf(self, info_object: InfoObject, files: list[MediaFile]) -> str:
        tags = [tag.name for tag in info_object.tags] if info_object.tags else []
        files_text = "\n".join(file.original_name for file in files) if files else "Нет вложений"

        parts = [
            r"{\rtf1\ansi\deff0",
            r"\b Заголовок:\b0 " + _rtf_escape(info_object.title or "") + r"\par",
            r"\b Текст:\b0 " + _rtf_escape(info_object.content or "") + r"\par",
            r"\b Источник:\b0 " + _rtf_escape(info_object.source or "") + r"\par",
            r"\b Автор:\b0 " + _rtf_escape(info_object.author or "") + r"\par",
            r"\b DOI:\b0 " + _rtf_escape(info_object.doi or "") + r"\par",
            r"\b Название публикации:\b0 " + _rtf_escape(info_object.publication_title or "") + r"\par",
            r"\b URL:\b0 " + _rtf_escape(info_object.url or "") + r"\par",
            r"\b Дата от:\b0 " + _rtf_escape(info_object.publication_date_from_raw or "") + r"\par",
            r"\b Дата до:\b0 " + _rtf_escape(info_object.publication_date_to_raw or "") + r"\par",
            r"\b Метки:\b0 " + _rtf_escape("\n".join(tags) if tags else "") + r"\par",
            r"\b Номер инф.объекта в БД:\b0 " + str(info_object.id) + r"\par",
            r"\b Объект создан:\b0 " + str(info_object.created_at) + r"\par",
            r"\b Создан пользователем:\b0 " + str(info_object.created_by or "") + r"\par",
            r"\b Вложения:\b0 " + _rtf_escape(files_text) + r"\par",
            r"}",
        ]
        return "".join(parts)

    def build_export_zip(self, info_object: InfoObject) -> bytes:
        files = self.get_files_for_info_object(info_object.id)
        rtf_content = self.build_rtf(info_object, files)

        buffer = BytesIO()
        with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr(f"info_object_{info_object.id}.rtf", rtf_content.encode("utf-8"))

            for file in files:
                path = Path(file.file_path)
                if path.exists():
                    archive.write(path, arcname=file.original_name)

        buffer.seek(0)
        return buffer.getvalue()