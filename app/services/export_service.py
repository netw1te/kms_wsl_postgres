from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.orm import Session

from app.models.info_object import InfoObject
from app.models.info_object_attachment import InfoObjectAttachment
from app.models.media_file import MediaFile


def _rtf_escape(text: str) -> str:
    text = (
        text.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
    )

    result = []
    for char in text:
        code = ord(char)
        if code > 127:
            if code > 32767:
                code -= 65536
            result.append(f"\\u{code}?")
        elif char == "\n":
            result.append("\\par ")
        else:
            result.append(char)

    return "".join(result)


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

        def _line(label: str, value: str) -> str:
            return f"\\b {_rtf_escape(label)}\\b0 {_rtf_escape(value)}\\par"

        parts = [
            r"{\rtf1\ansi\deff0",
            _line("Заголовок:", info_object.title or ""),
            _line("Текст:", info_object.content or ""),
            _line("Источник:", info_object.source or ""),
            _line("Автор:", info_object.author or ""),
            _line("DOI:", info_object.doi or ""),
            _line("Название публикации:", info_object.publication_title or ""),
            _line("URL:", info_object.url or ""),
            _line("Дата от:", info_object.publication_date_from_raw or ""),
            _line("Дата до:", info_object.publication_date_to_raw or ""),
            _line("Метки:", ", ".join(tags) if tags else ""),
            _line("Номер инф.объекта в БД:", str(info_object.id)),
            _line("Объект создан:", str(info_object.created_at)),
            _line("Создан пользователем:", str(info_object.created_by or "")),
            _line("Вложения:", files_text),
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