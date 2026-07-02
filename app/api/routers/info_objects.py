from datetime import datetime
from typing import List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session, aliased, joinedload

from app.auth import CurrentUser, get_current_user, require_data_admin
from app.database import get_db
from app.models.info_object import InfoObject, Tag
from app.models.user import User
from app.models.info_object_deletion_request import InfoObjectDeletionRequest
from app.services.info_object_service import InfoObjectService
from app.services.ownership_service import ensure_can_modify_info_object
from app.services.complex_query_service import ComplexQueryService
from app.schemas.complex_query import ComplexQuery
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

    publication_date_raw: Optional[str] = None
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

    publication_date_raw: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class InfoObjectResponse(BaseModel):
    id: int
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    author_name: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None

    publication_title: Optional[str] = None
    publication_date_from_raw: Optional[str] = None
    publication_date_to_raw: Optional[str] = None
    publication_date_from: Optional[datetime] = None
    publication_date_to: Optional[datetime] = None

    publication_date_raw: Optional[str] = None
    publication_date: Optional[datetime] = None

    tags: List[str] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None

    deletion_flag: bool = False
    deletion_reason: Optional[str] = None
    deleted_by: Optional[int] = None
    replacement_info_object_id: Optional[int] = None


class PageResponse(BaseModel):
    items: List[InfoObjectResponse]
    total: int
    page: int
    size: int
    pages: int


def serialize_info_object(obj: InfoObject) -> dict:
    resolved_author = obj.author
    if obj.author_user and obj.author_user.full_name:
        resolved_author = obj.author_user.full_name
    elif obj.author_user and obj.author_user.login:
        resolved_author = obj.author_user.login
    elif obj.creator and obj.creator.full_name:
        resolved_author = obj.creator.full_name
    elif obj.creator and obj.creator.login:
        resolved_author = obj.creator.login

    return {
        "id": obj.id,
        "title": obj.title,
        "content": obj.content,
        "source": obj.source,
        "author": resolved_author,
        "author_name": obj.creator.full_name if (obj.creator and obj.creator.full_name) else None,
        "url": obj.url,
        "doi": obj.doi,
        "publication_title": obj.publication_title,
        "publication_date_from_raw": obj.publication_date_from_raw,
        "publication_date_to_raw": obj.publication_date_to_raw,
        "publication_date_from": obj.publication_date_from,
        "publication_date_to": obj.publication_date_to,
        "publication_date_raw": getattr(obj, "publication_date_raw", None),
        "publication_date": getattr(obj, "publication_date", None),
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

    raw_publication, normalized_publication = normalize_partial_date(payload.publication_date_raw, is_end=False)
    info_object.publication_date_raw = raw_publication
    info_object.publication_date = normalized_publication or datetime.utcnow()


def _apply_simple_search_filters(
        query,
        search_everywhere: Optional[str],
        title: Optional[str],
        text: Optional[str],
        author: Optional[str],
        source: Optional[str],
        publication_title: Optional[str],
        url: Optional[str],
        doi: Optional[str],
        tags: Optional[List[str]],
        tag_mode: str,
        publication_date_from: Optional[datetime],
        publication_date_to: Optional[datetime],
):
    SearchUser = aliased(User)

    if search_everywhere or author:
        query = query.outerjoin(
            SearchUser,
            or_(
                InfoObject.created_by == SearchUser.id,
                InfoObject.author == SearchUser.login
            )
        )

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
                SearchUser.full_name.ilike(pattern),
                SearchUser.login.ilike(pattern),
            )
        )

    if title:
        query = query.filter(InfoObject.title.ilike(f"%{title}%"))
    if text:
        query = query.filter(InfoObject.content.ilike(f"%{text}%"))
    if author:
        pattern = f"%{author}%"
        query = query.filter(
            or_(
                InfoObject.author.ilike(pattern),
                SearchUser.full_name.ilike(pattern),
                SearchUser.login.ilike(pattern),
            )
        )
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

    if publication_date_from:
        query = query.filter(InfoObject.publication_date >= publication_date_from)
    if publication_date_to:
        query = query.filter(InfoObject.publication_date <= publication_date_to)

    return query


def _paginate(query, page: int, size: int, sort: str, direction: str):
    sort_field = getattr(InfoObject, sort, InfoObject.id)
    order_clause = asc(sort_field) if direction.lower() == "asc" else desc(sort_field)
    query = query.order_by(order_clause)

    total = query.count()

    query = query.options(
        joinedload(InfoObject.creator),
        joinedload(InfoObject.author_user),
        joinedload(InfoObject.tags)
    )

    items = query.offset(page * size).limit(size).all()
    pages = (total + size - 1) // size if total else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.get("/my", response_model=PageResponse)
async def get_my_info_objects(
        page: int = Query(0, ge=0),
        size: int = Query(20, ge=1, le=100),
        sort: str = Query("id"),
        direction: str = Query("asc"),
        include_deleted: bool = Query(False),
        db: Session = Depends(get_db),
        current_user: CurrentUser = Depends(get_current_user),
):
    service = InfoObjectService(db)
    result = service.find_my(
        user_id=current_user.id,
        page=page,
        size=size,
        sort=sort,
        direction=direction,
        include_deleted=include_deleted,
    )

    return PageResponse(
        items=[InfoObjectResponse(**serialize_info_object(item)) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"],
    )


@router.get("/search", response_model=PageResponse)
async def search_info_objects(
        search_everywhere: str | None = Query(None),
        title: str | None = Query(None),
        text: str | None = Query(None),
        author: str | None = Query(None),
        source: str | None = Query(None),
        publication_title: str | None = Query(None),
        url: str | None = Query(None),
        doi: str | None = Query(None),
        tags: list[str] | None = Query(None),
        tag_mode: str = Query("AND", pattern="^(AND|OR)$"),
        publication_date_from_raw: str | None = Query(None),
        publication_date_to_raw: str | None = Query(None),
        include_deleted: bool = Query(False),
        page: int = Query(0, ge=0),
        size: int = Query(20, ge=1, le=100),
        sort: str = Query("id"),
        direction: str = Query("asc"),
        complex_query_json: str | None = Query(None),
        db: Session = Depends(get_db),
        current_user: CurrentUser = Depends(get_current_user),
):
    if complex_query_json:
        try:
            query_data = json.loads(complex_query_json)
            complex_query = ComplexQuery(**query_data)

            query = db.query(InfoObject)

            complex_service = ComplexQueryService(db)
            query = complex_service.build_query(query, complex_query)

            result = _paginate(query, page, size, sort, direction)

            return PageResponse(
                items=[InfoObjectResponse(**serialize_info_object(item)) for item in result["items"]],
                total=result["total"],
                page=result["page"],
                size=result["size"],
                pages=result["pages"],
            )

        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Ошибка парсинга JSON сложного запроса: {str(exc)}")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Ошибка обработки сложного запроса: {str(exc)}")

    _, publication_date_from = normalize_partial_date(publication_date_from_raw, is_end=False)
    _, publication_date_to = normalize_partial_date(publication_date_to_raw, is_end=True)

    query = db.query(InfoObject)

    query = _apply_simple_search_filters(
        query=query,
        search_everywhere=search_everywhere,
        title=title,
        text=text,
        author=author,
        source=source,
        publication_title=publication_title,
        url=url,
        doi=doi,
        tags=tags,
        tag_mode=tag_mode,
        publication_date_from=publication_date_from,
        publication_date_to=publication_date_to,
    )

    result = _paginate(query, page, size, sort, direction)

    return PageResponse(
        items=[InfoObjectResponse(**serialize_info_object(item)) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"],
    )


@router.post("/complex-search", response_model=PageResponse)
async def complex_search_post(
        complex_query: ComplexQuery,
        page: int = Query(0, ge=0),
        size: int = Query(20, ge=1, le=100),
        sort: str = Query("id"),
        direction: str = Query("asc"),
        include_deleted: bool = Query(False),
        db: Session = Depends(get_db),
        current_user: CurrentUser = Depends(get_current_user),
):
    query = db.query(InfoObject)

    complex_service = ComplexQueryService(db)
    query = complex_service.build_query(query, complex_query)

    result = _paginate(query, page, size, sort, direction)

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
        include_deleted: bool = Query(False),
        db: Session = Depends(get_db),
        current_user: CurrentUser = Depends(get_current_user),
):
    service = InfoObjectService(db)
    result = service.find_all(
        page=page,
        size=size,
        sort=sort,
        direction=direction,
        include_deleted=include_deleted,
    )

    return PageResponse(
        items=[InfoObjectResponse(**serialize_info_object(item)) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"],
    )


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


@router.get("/deleted", response_model=PageResponse)
async def get_deleted_info_objects(
        page: int = Query(0, ge=0),
        size: int = Query(20, ge=1, le=100),
        sort: str = Query("deleted_at"),
        direction: str = Query("desc"),
        db: Session = Depends(get_db),
        current_admin: CurrentUser = Depends(require_data_admin),
):
    service = InfoObjectService(db)
    service.purge_deleted_older_than(days=7)
    result = service.find_deleted(page=page, size=size, sort=sort, direction=direction)

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
    item = (
        db.query(InfoObject)
        .options(
            joinedload(InfoObject.creator),
            joinedload(InfoObject.author_user),
            joinedload(InfoObject.tags)
        )
        .filter(InfoObject.id == info_object_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="InfoObject not found")
    return InfoObjectResponse(**serialize_info_object(item))


@router.put("/{info_object_id}", response_model=InfoObjectResponse)
async def update_info_object(
        info_object_id: int,
        payload: InfoObjectUpdate,
        db: Session = Depends(get_db),
        current_user: CurrentUser = Depends(get_current_user),
):
    service = InfoObjectService(db)
    info_object = (
        db.query(InfoObject)
        .options(joinedload(InfoObject.tags))
        .filter(InfoObject.id == info_object_id)
        .first()
    )
    if not info_object:
        raise HTTPException(status_code=404, detail="InfoObject not found")

    ensure_can_modify_info_object(current_user, info_object)

    apply_payload(info_object, payload)

    info_object.tags.clear()
    db.flush()

    new_tags = service.get_or_create_tags(payload.tags)
    info_object.tags.extend(new_tags)

    if info_object.publication_date is None:
        info_object.publication_date = datetime.utcnow()
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

    ensure_can_modify_info_object(current_user, info_object)

    info_object.deletion_flag = True
    info_object.deletion_reason = reason
    info_object.deleted_by = current_user.id
    info_object.replacement_info_object_id = replacement_info_object_id
    info_object.deleted_at = datetime.utcnow()

    # Also automatically file a deletion request so it is visible to Admins
    existing_req = db.query(InfoObjectDeletionRequest).filter(
        InfoObjectDeletionRequest.info_object_id == info_object_id,
        InfoObjectDeletionRequest.status == "pending"
    ).first()

    if not existing_req:
        new_req = InfoObjectDeletionRequest(
            info_object_id=info_object_id,
            requested_by=current_user.id,
            reason=reason,
            replacement_info_object_id=replacement_info_object_id,
            status="pending"
        )
        db.add(new_req)

    db.commit()
    db.refresh(info_object)
    return InfoObjectResponse(**serialize_info_object(info_object))


@router.patch("/{info_object_id}/restore", response_model=InfoObjectResponse)
async def restore_info_object(
        info_object_id: int,
        db: Session = Depends(get_db),
        current_admin: CurrentUser = Depends(require_data_admin),
):
    service = InfoObjectService(db)
    restored = service.restore_info_object(info_object_id)
    if not restored:
        raise HTTPException(status_code=404, detail="InfoObject not found")
    return InfoObjectResponse(**serialize_info_object(restored))


@router.delete("/{info_object_id}/hard-delete", status_code=status.HTTP_204_NO_CONTENT)
async def hard_delete_info_object(
        info_object_id: int,
        db: Session = Depends(get_db),
        current_admin: CurrentUser = Depends(require_data_admin),
):
    service = InfoObjectService(db)
    ok = service.hard_delete_info_object(info_object_id)
    if not ok:
        raise HTTPException(status_code=404, detail="InfoObject not found")


@router.get("/{info_object_id}/export")
async def export_info_object(
        info_object_id: int,
        db: Session = Depends(get_db),
        current_user: CurrentUser = Depends(get_current_user),
):
    service = ExportService(db)
    info_object = service.get_info_object_or_none(info_object_id)
    if not info_object:
        raise HTTPException(status_code=404, detail="InfoObject not found")

    data = service.build_export_zip(info_object)
    filename = f"info_object_{info_object_id}.zip"

    return StreamingResponse(
        BytesIO(data),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )