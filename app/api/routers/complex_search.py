from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models.info_object import InfoObject
from app.schemas.complex_query import ComplexQuery
from app.schemas.info_object import InfoObjectResponse, PageResponse
from app.services.complex_query_service import ComplexQueryService


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
        "publication_date_raw": obj.publication_date_raw,
        "publication_date": obj.publication_date,
        "tags": [tag.name for tag in obj.tags],
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
        "created_by": obj.created_by,
        "deletion_flag": bool(obj.deletion_flag),
        "deletion_reason": obj.deletion_reason,
        "deleted_by": obj.deleted_by,
        "deleted_at": getattr(obj, "deleted_at", None),
        "replacement_info_object_id": obj.replacement_info_object_id,
    }


router = APIRouter(prefix="/complex-search", tags=["Сложный поиск"])


@router.post("", response_model=PageResponse)
async def complex_search(
        complex_query: ComplexQuery,
        page: int = Query(0, ge=0),
        size: int = Query(20, ge=1, le=100),
        sort: str = Query("id"),
        direction: str = Query("asc"),
        include_deleted: bool = Query(False),
        db: Session = Depends(get_db),
        current_user: CurrentUser = Depends(get_current_user),
):
    service = ComplexQueryService(db)

    query = db.query(InfoObject)

    if not include_deleted:
        query = query.filter(
            or_(
                InfoObject.deletion_flag.is_(False),
                InfoObject.deletion_flag.is_(None),
            )
        )

    try:
        query = service.build_query(query, complex_query)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка построения сложного запроса: {str(exc)}"
        )

    total = query.count()

    sort_field = getattr(InfoObject, sort, InfoObject.id)
    order_clause = asc(sort_field) if direction.lower() == "asc" else desc(sort_field)

    items = query.order_by(order_clause).offset(page * size).limit(size).all()

    pages = (total + size - 1) // size if total else 0

    serialized_items = []
    for item in items:
        try:
            serialized_items.append(InfoObjectResponse(**serialize_info_object(item)))
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка сериализации объекта {item.id}: {str(exc)}"
            )

    return PageResponse(
        items=serialized_items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )