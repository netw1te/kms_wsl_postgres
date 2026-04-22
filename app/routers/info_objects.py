from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user, require_admin
from app.database import get_db
from app.models.info_object import InfoObject
from app.services.info_object_service import InfoObjectService
from app.utils.date_parser import normalize_partial_date
from fastapi.responses import StreamingResponse
from io import BytesIO

from app.services.export_service import ExportService

router = APIRouter(prefix="/info-objects", tags=["Информационные объекты"])


class InfoObjectCreate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None

    publication_title: Optional[str] = None
    publication_date_from_raw: Optional[str] = None
    publication_date_to_raw: Optional[str] = None

    tags: List[str] = Field(default_factory=list)


class InfoObjectUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None

    publication_title: Optional[str] = None
    publication_date_from_raw: Optional[str] = None
    publication_date_to_raw: Optional[str] = None

    tags: List[str] = Field(default_factory=list)


class InfoObjectResponse(BaseModel):
    id: int
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None

    publication_title: Optional[str] = None
    publication_date_from_raw: Optional[str] = None
    publication_date_to_raw: Optional[str] = None
    publication_date_from: Optional[datetime] = None
    publication_date_to: Optional[datetime] = None

    tags: List[str] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None

    deletion_flag: bool = False
    deletion_reason: Optional[str] = None
    deleted_by: Optional[int] = None
    replacement_info_object_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PageResponse(BaseModel):
    items: List[InfoObjectResponse]
    total: int
    page: int
    size: int
    pages: int


def serialize_info_object(obj: InfoObject) -> dict:
    return {
        "id": obj.id,
        "title": obj.title,
        "content": obj.content,
        "source": obj.source,
        "author": obj.author,
        "url": obj.url,
        "doi": obj.doi,
        "publication_title": obj.publication_title,
        "publication_date_from_raw": obj.publication_date_from_raw,
        "publication_date_to_raw": obj.publication_date_to_raw,
        "publication_date_from": obj.publication_date_from,
        "publication_date_to": obj.publication_date_to,
        "tags": [tag.name for tag in obj.tags],
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
        "created_by": obj.created_by,
        "deletion_flag": bool(obj.deletion_flag),
        "deletion_reason": obj.deletion_reason,
        "deleted_by": obj.deleted_by,
        "replacement_info_object_id": obj.replacement_info_object_id,
    }


def apply_payload(info_object: InfoObject, payload: InfoObjectCreate | InfoObjectUpdate):
    info_object.title = payload.title
    info_object.content = payload.content
    info_object.source = payload.source
    info_object.author = payload.author
    info_object.url = payload.url
    info_object.doi = payload.doi
    info_object.publication_title = payload.publication_title

    raw_from, normalized_from = normalize_partial_date(payload.publication_date_from_raw, is_end=False)
    raw_to, normalized_to = normalize_partial_date(payload.publication_date_to_raw, is_end=True)

    info_object.publication_date_from_raw = raw_from
    info_object.publication_date_to_raw = raw_to
    info_object.publication_date_from = normalized_from
    info_object.publication_date_to = normalized_to


@router.get("/search", response_model=PageResponse)
async def search_info_objects(
    title: str | None = Query(None),
    text: str | None = Query(None),
    author: str | None = Query(None),
    source: str | None = Query(None),
    publication_title: str | None = Query(None),
    doi: str | None = Query(None),
    tags: list[str] | None = Query(None),
    tag_mode: str = Query("AND", pattern="^(AND|OR)$"),
    include_deleted: bool = Query(False),
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
    sort: str = Query("id"),
    direction: str = Query("asc"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = InfoObjectService(db)
    try:
        result = service.search(
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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PageResponse(
        items=[InfoObjectResponse(**serialize_info_object(item)) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"],
    )


@router.get("", response_model=PageResponse)
async def get_all_info_objects(
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
    sort: str = Query("id"),
    direction: str = Query("asc"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = InfoObjectService(db)
    result = service.find_all(page=page, size=size, sort=sort, direction=direction)

    return PageResponse(
        items=[InfoObjectResponse(**serialize_info_object(item)) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"],
    )


@router.get("/{info_object_id}", response_model=InfoObjectResponse)
async def get_info_object_by_id(
    info_object_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = InfoObjectService(db)
    info_object = service.find_by_id(info_object_id)
    if not info_object:
        raise HTTPException(status_code=404, detail="InfoObject not found")
    return InfoObjectResponse(**serialize_info_object(info_object))


@router.post("", response_model=InfoObjectResponse, status_code=status.HTTP_201_CREATED)
async def create_info_object(
    payload: InfoObjectCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = InfoObjectService(db)
    info_object = InfoObject(created_by=current_user.id)
    apply_payload(info_object, payload)
    info_object.tags = service.get_or_create_tags(payload.tags)

    saved = service.save(info_object)
    return InfoObjectResponse(**serialize_info_object(saved))


@router.put("/{info_object_id}", response_model=InfoObjectResponse)
async def update_info_object(
    info_object_id: int,
    payload: InfoObjectUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = InfoObjectService(db)
    info_object = service.find_by_id(info_object_id)
    if not info_object:
        raise HTTPException(status_code=404, detail="InfoObject not found")

    apply_payload(info_object, payload)
    info_object.tags = service.get_or_create_tags(payload.tags)

    saved = service.save(info_object)
    return InfoObjectResponse(**serialize_info_object(saved))


@router.patch("/{info_object_id}/soft-delete", response_model=InfoObjectResponse)
async def soft_delete_info_object(
    info_object_id: int,
    reason: str | None = Query(None),
    replacement_info_object_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = InfoObjectService(db)
    info_object = service.find_by_id(info_object_id)
    if not info_object:
        raise HTTPException(status_code=404, detail="InfoObject not found")

    info_object.deletion_flag = True
    info_object.deletion_reason = reason
    info_object.deleted_by = current_user.id
    info_object.replacement_info_object_id = replacement_info_object_id

    saved = service.save(info_object)
    return InfoObjectResponse(**serialize_info_object(saved))


@router.patch("/{info_object_id}/restore", response_model=InfoObjectResponse)
async def restore_info_object(
    info_object_id: int,
    db: Session = Depends(get_db),
    current_admin: CurrentUser = Depends(require_admin),
):
    service = InfoObjectService(db)
    restored = service.restore_info_object(info_object_id)
    if not restored:
        raise HTTPException(status_code=404, detail="InfoObject not found")
    return InfoObjectResponse(**serialize_info_object(restored))


@router.delete("/{info_object_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_info_object(
    info_object_id: int,
    db: Session = Depends(get_db),
    current_admin: CurrentUser = Depends(require_admin),
):
    service = InfoObjectService(db)
    if not service.exists_by_id(info_object_id):
        raise HTTPException(status_code=404, detail="InfoObject not found")
    service.delete_by_id(info_object_id)