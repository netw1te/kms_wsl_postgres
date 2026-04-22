import hashlib
import os
import re
from pathlib import Path
from typing import Sequence

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.info_object import InfoObject
from app.models.info_object_attachment import InfoObjectAttachment
from app.models.media_file import MediaFile


class MediaFileService:
    def __init__(self, db: Session):
        self.db = db
        self.upload_dir = Path(os.getenv("UPLOAD_DIR", "storage/uploads"))
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", filename)
        return safe[:200] if safe else "file"

    @staticmethod
    def _deny_executable_extension(filename: str) -> None:
        denied = {
            ".exe", ".bat", ".cmd", ".com", ".msi", ".sh", ".ps1",
            ".js", ".jar", ".scr", ".vbs", ".dll"
        }
        ext = Path(filename).suffix.lower()
        if ext in denied:
            raise HTTPException(
                status_code=400,
                detail=f"Файл с расширением {ext} запрещён для загрузки.",
            )
    def _ensure_can_read_info_object(
    self,
    info_object: InfoObject,
    current_user_id: int | None,
    is_admin: bool,
    ) -> None:
        if is_admin:
            return
        if info_object.created_by != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы можете просматривать вложения только у своих информационных объектов.",
            )

    def _get_info_object(self, info_object_id: int) -> InfoObject:
        info_object = self.db.query(InfoObject).filter(InfoObject.id == info_object_id).first()
        if info_object is None:
            raise HTTPException(status_code=404, detail="InfoObject not found")
        return info_object

    @staticmethod
    def _ensure_can_manage_info_object(
        info_object: InfoObject,
        current_user_id: int | None,
        is_admin: bool,
    ) -> None:
        if is_admin:
            return
        if info_object.created_by != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы можете изменять вложения только у своих информационных объектов.",
            )

    def list_for_info_object(
    self,
    info_object_id: int,
    current_user_id: int | None,
    is_admin: bool = False,
    ) -> list[MediaFile]:
        info_object = self._get_info_object(info_object_id)
        self._ensure_can_read_info_object(info_object, current_user_id, is_admin)

        rows = (
            self.db.query(MediaFile)
            .join(InfoObjectAttachment, InfoObjectAttachment.media_file_id == MediaFile.id)
            .filter(InfoObjectAttachment.info_object_id == info_object_id)
            .order_by(MediaFile.id.asc())
            .all()
        )
        return rows

    def get_file(self, file_id: int) -> MediaFile:
        media_file = self.db.query(MediaFile).filter(MediaFile.id == file_id).first()
        if media_file is None:
            raise HTTPException(status_code=404, detail="Файл не найден")
        return media_file

    async def attach_files(
        self,
        info_object_id: int,
        files: Sequence[UploadFile],
        current_user_id: int | None,
        is_admin: bool = False,
    ) -> list[MediaFile]:
        info_object = self._get_info_object(info_object_id)
        self._ensure_can_manage_info_object(info_object, current_user_id, is_admin)

        if not files:
            raise HTTPException(status_code=400, detail="Файлы не переданы")

        if len(files) > 3:
            raise HTTPException(status_code=400, detail="Можно прикрепить не более 3 файлов за раз")

        attached_files: list[MediaFile] = []

        for upload in files:
            filename = upload.filename or "file"
            self._deny_executable_extension(filename)

            content = await upload.read()
            if not content:
                raise HTTPException(status_code=400, detail=f"Файл {filename} пустой")

            checksum = hashlib.sha256(content).hexdigest()

            media_file = (
                self.db.query(MediaFile)
                .filter(MediaFile.checksum_sha256 == checksum)
                .first()
            )

            if media_file is None:
                safe_name = self._sanitize_filename(filename)
                stored_name = f"{checksum}_{safe_name}"
                file_path = self.upload_dir / stored_name

                if not file_path.exists():
                    file_path.write_bytes(content)

                media_file = MediaFile(
                    original_name=filename,
                    stored_name=stored_name,
                    file_path=str(file_path),
                    content_type=upload.content_type,
                    size_bytes=len(content),
                    checksum_sha256=checksum,
                    uploaded_by=current_user_id,
                )
                self.db.add(media_file)
                self.db.flush()

            link = (
                self.db.query(InfoObjectAttachment)
                .filter(
                    InfoObjectAttachment.info_object_id == info_object_id,
                    InfoObjectAttachment.media_file_id == media_file.id,
                )
                .first()
            )
            if link is None:
                self.db.add(
                    InfoObjectAttachment(
                        info_object_id=info_object_id,
                        media_file_id=media_file.id,
                    )
                )

            attached_files.append(media_file)

        self.db.commit()
        return attached_files

    def detach_file(
        self,
        info_object_id: int,
        file_id: int,
        current_user_id: int | None,
        is_admin: bool = False,
    ) -> None:
        info_object = self._get_info_object(info_object_id)
        self._ensure_can_manage_info_object(info_object, current_user_id, is_admin)

        media_file = self.get_file(file_id)

        link = (
            self.db.query(InfoObjectAttachment)
            .filter(
                InfoObjectAttachment.info_object_id == info_object_id,
                InfoObjectAttachment.media_file_id == file_id,
            )
            .first()
        )
        if link is None:
            raise HTTPException(status_code=404, detail="Связь файла с ИО не найдена")

        self.db.delete(link)
        self.db.flush()

        remaining_links = (
            self.db.query(InfoObjectAttachment)
            .filter(InfoObjectAttachment.media_file_id == file_id)
            .count()
        )

        if remaining_links == 0:
            file_path = Path(media_file.file_path)
            if file_path.exists():
                file_path.unlink()
            self.db.delete(media_file)

        self.db.commit()
    def get_file_for_info_object(
    self,
    info_object_id: int,
    file_id: int,
    current_user_id: int | None,
    is_admin: bool = False,
    ) -> MediaFile:
        info_object = self._get_info_object(info_object_id)
        self._ensure_can_read_info_object(info_object, current_user_id, is_admin)

        media_file = (
            self.db.query(MediaFile)
            .join(InfoObjectAttachment, InfoObjectAttachment.media_file_id == MediaFile.id)
            .filter(
                InfoObjectAttachment.info_object_id == info_object_id,
                MediaFile.id == file_id,
            )
            .first()
        )
        if media_file is None:
            raise HTTPException(status_code=404, detail="Файл не найден")
        return media_file