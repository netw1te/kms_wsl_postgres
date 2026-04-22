from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models.search_query import SearchQuery
from app.services.search_query_service import SearchQueryService


router = APIRouter(prefix="/search-queries", tags=["Поисковые запросы"])


class SearchQueryCreate(BaseModel):
    name: str

    search_everywhere: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    publication_title: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None

    tags: List[str] = Field(default_factory=list)
    tag_mode: str = "AND"

    created_after_raw: Optional[str] = None
    created_before_raw: Optional[str] = None

    info_object_id: Optional[int] = None


class SearchQueryRename(BaseModel):
    name: str


class SearchQueryResponse(BaseModel):
    id: int
    created_at: datetime
    name: str

    search_everywhere: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    publication_title: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None

    tags: List[str] = Field(default_factory=list)
    tag_mode: Optional[str] = None

    created_after_raw: Optional[str] = None
    created_before_raw: Optional[str] = None

    info_object_id: Optional[int] = None
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class SearchQueryListResponse(BaseModel):
    items: List[SearchQueryResponse]
    total: int


def _to_response(item: SearchQuery) -> SearchQueryResponse:
    tags = []
    if item.tags_text:
        tags = [x for x in item.tags_text.split("\n") if x.strip()]

    return SearchQueryResponse(
        id=item.id,
        created_at=item.created_at,
        name=item.name,
        search_everywhere=item.search_everywhere,
        title=item.title,
        text=item.text,
        source=item.source,
        author=item.author,
        publication_title=item.publication_title,
        url=item.url,
        doi=item.doi,
        tags=tags,
        tag_mode=item.tag_mode,
        created_after_raw=item.created_after_raw,
        created_before_raw=item.created_before_raw,
        info_object_id=item.info_object_id,
        user_id=item.user_id,
    )


@router.post("/", response_model=SearchQueryResponse, status_code=status.HTTP_201_CREATED)
async def create_search_query(
    payload: SearchQueryCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = SearchQueryService(db)

    query = SearchQuery(
        name=payload.name,
        search_everywhere=payload.search_everywhere,
        title=payload.title,
        text=payload.text,
        source=payload.source,
        author=payload.author,
        publication_title=payload.publication_title,
        url=payload.url,
        doi=payload.doi,
        tags_text="\n".join(payload.tags) if payload.tags else None,
        tag_mode=payload.tag_mode,
        created_after_raw=payload.created_after_raw,
        created_before_raw=payload.created_before_raw,
        info_object_id=payload.info_object_id,
        user_id=current_user.id,
    )

    saved = service.create(query)
    return _to_response(saved)


@router.get("/my", response_model=SearchQueryListResponse)
async def get_my_search_queries(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = SearchQueryService(db)
    result = service.get_my_queries(current_user.id, skip, limit)

    return SearchQueryListResponse(
        items=[_to_response(item) for item in result["items"]],
        total=result["total"],
    )


@router.get("/{search_query_id}", response_model=SearchQueryResponse)
async def get_search_query(
    search_query_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = SearchQueryService(db)

    item = service.get_by_id(search_query_id)
    if not item:
        raise HTTPException(status_code=404, detail="Запрос не найден")

    if item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Чужие запросы недоступны")

    return _to_response(item)


@router.put("/{search_query_id}/rename", response_model=SearchQueryResponse)
async def rename_search_query(
    search_query_id: int,
    payload: SearchQueryRename,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = SearchQueryService(db)

    item = service.get_by_id(search_query_id)
    if not item:
        raise HTTPException(status_code=404, detail="Запрос не найден")

    if item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Чужие запросы недоступны")

    updated = service.rename(item, payload.name)
    return _to_response(updated)


@router.delete("/{search_query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search_query(
    search_query_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    service = SearchQueryService(db)

    item = service.get_by_id(search_query_id)
    if not item:
        raise HTTPException(status_code=404, detail="Запрос не найден")

    if item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Чужие запросы недоступны")

    service.delete(item)