import re
from typing import Optional
from urllib.parse import urlencode

from app.models.search_query import SearchQuery
from app.services.search_query_service import SearchQueryService
from fastapi import APIRouter, Depends, Form, Query, Request, UploadFile, File
from app.services.media_file_service import MediaFileService
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import authenticate_user
from app.database import get_db
from app.models.info_object import InfoObject
from app.models.search_query import SearchQuery
from app.services.info_object_service import InfoObjectService
from app.utils.date_parser import normalize_partial_date


router = APIRouter(tags=["Web"])
templates = Jinja2Templates(directory="templates")


def session_user(request: Request) -> Optional[dict]:
    user = request.session.get("user")
    return user if isinstance(user, dict) else None


def require_session_user(request: Request):
    user = session_user(request)
    if not user:
        return None
    return user

def session_user_is_admin(user: dict) -> bool:
    role = user.get("role", "")
    return "ROLE_ADMIN" in [item.strip() for item in role.split(",") if item.strip()]

def parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[,;\n]+", raw)
    return [part.strip() for part in parts if part.strip()]


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = session_user(request)
    if user:
        return RedirectResponse(url="/app", status_code=303)

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": None,
            "session_user": None,
        },
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, login, password)
    if user is None:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Неверный логин или пароль",
                "session_user": None,
            },
            status_code=401,
        )

    request.session["user"] = {
        "id": user.id,
        "login": user.login,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
    }
    return RedirectResponse(url="/app", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/app", response_class=HTMLResponse)
async def app_home(request: Request, db: Session = Depends(get_db)):
    user = require_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    total_info_objects = db.query(InfoObject).count()
    my_queries_count = db.query(SearchQuery).filter(SearchQuery.user_id == user["id"]).count()

    return templates.TemplateResponse(
        "app_home.html",
        {
            "request": request,
            "session_user": user,
            "total_info_objects": total_info_objects,
            "my_queries_count": my_queries_count,
        },
    )


@router.get("/app/info-objects", response_class=HTMLResponse)
async def app_info_objects(
    request: Request,
    title: str | None = Query(None),
    text: str | None = Query(None),
    author: str | None = Query(None),
    source: str | None = Query(None),
    publication_title: str | None = Query(None),
    doi: str | None = Query(None),
    tags: str | None = Query(None),
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    user = require_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    service = InfoObjectService(db)
    parsed_tags = parse_tags(tags)

    error = None
    if any([title, text, author, source, publication_title, doi, parsed_tags]):
        try:
            result = service.search(
                title=title,
                text=text,
                author=author,
                source=source,
                publication_title=publication_title,
                doi=doi,
                tags=parsed_tags or None,
                tag_mode="AND",
                include_deleted=False,
                page=page,
                size=size,
                sort="id",
                direction="asc",
            )
        except ValueError as exc:
            error = str(exc)
            result = {"items": [], "total": 0, "page": page, "size": size, "pages": 0}
    else:
        result = service.find_all(page=page, size=size, sort="id", direction="asc")

    return templates.TemplateResponse(
        "info_objects_list.html",
        {
            "request": request,
            "session_user": user,
            "items": result["items"],
            "total": result["total"],
            "page": result["page"],
            "size": result["size"],
            "pages": result["pages"],
            "filters": {
                "title": title or "",
                "text": text or "",
                "author": author or "",
                "source": source or "",
                "publication_title": publication_title or "",
                "doi": doi or "",
                "tags": tags or "",
            },
            "error": error,
        },
    )


@router.get("/app/info-objects/new", response_class=HTMLResponse)
async def app_new_info_object(request: Request):
    user = require_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "info_objects_new.html",
        {
            "request": request,
            "session_user": user,
            "error": None,
        },
    )


@router.post("/app/info-objects/new", response_class=HTMLResponse)
async def app_create_info_object(
    request: Request,
    title: str = Form(""),
    content: str = Form(""),
    source: str = Form(""),
    author: str = Form(""),
    url: str = Form(""),
    doi: str = Form(""),
    publication_title: str = Form(""),
    publication_date_from_raw: str = Form(""),
    publication_date_to_raw: str = Form(""),
    tags_text: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    service = InfoObjectService(db)

    entity = InfoObject(
        title=title or None,
        content=content or None,
        source=source or None,
        author=author or None,
        url=url or None,
        doi=doi or None,
        publication_title=publication_title or None,
        created_by=user["id"],
    )

    raw_from, normalized_from = normalize_partial_date(publication_date_from_raw or None, is_end=False)
    raw_to, normalized_to = normalize_partial_date(publication_date_to_raw or None, is_end=True)

    entity.publication_date_from_raw = raw_from
    entity.publication_date_to_raw = raw_to
    entity.publication_date_from = normalized_from
    entity.publication_date_to = normalized_to

    entity.tags = service.get_or_create_tags(parse_tags(tags_text))
    saved = service.save(entity)

    return RedirectResponse(url=f"/app/info-objects/{saved.id}", status_code=303)
@router.get("/app/info-objects/{info_object_id}", response_class=HTMLResponse)
async def app_info_object_detail(
    request: Request,
    info_object_id: int,
    db: Session = Depends(get_db),
):
    user = require_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    service = InfoObjectService(db)
    files_service = MediaFileService(db)

    item = service.find_by_id(info_object_id)
    if item is None:
        return templates.TemplateResponse(
            "info_object_detail.html",
            {
                "request": request,
                "session_user": user,
                "item": None,
                "files": [],
                "error": "Информационный объект не найден",
            },
            status_code=404,
        )

    files = files_service.list_for_info_object(info_object_id)

    return templates.TemplateResponse(
        "info_object_detail.html",
        {
            "request": request,
            "session_user": user,
            "item": item,
            "files": files,
            "error": None,
        },
    )


@router.post("/app/info-objects/{info_object_id}/upload", response_class=HTMLResponse)
async def app_upload_files_to_info_object(
    request: Request,
    info_object_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    user = require_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    files_service = MediaFileService(db)
    await files_service.attach_files(
        info_object_id=info_object_id,
        files=files,
        current_user_id=user["id"],
        is_admin=session_user_is_admin(user),
    )
    return RedirectResponse(url=f"/app/info-objects/{info_object_id}", status_code=303)


@router.post("/app/info-objects/{info_object_id}/files/{file_id}/delete", response_class=HTMLResponse)
async def app_delete_file_from_info_object(
    request: Request,
    info_object_id: int,
    file_id: int,
    db: Session = Depends(get_db),
):
    user = require_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    files_service = MediaFileService(db)
    files_service.detach_file(
        info_object_id=info_object_id,
        file_id=file_id,
        current_user_id=user["id"],
        is_admin=session_user_is_admin(user),
    )
    return RedirectResponse(url=f"/app/info-objects/{info_object_id}", status_code=303)
@router.get("/app/info-objects/{info_object_id}/edit", response_class=HTMLResponse)
async def app_edit_info_object_page(
    request: Request,
    info_object_id: int,
    db: Session = Depends(get_db),
):
    user = require_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    service = InfoObjectService(db)
    item = service.find_by_id(info_object_id)

    if item is None:
        return templates.TemplateResponse(
            "info_objects_edit.html",
            {
                "request": request,
                "session_user": user,
                "item": None,
                "error": "Информационный объект не найден",
            },
            status_code=404,
        )

    if item.created_by != user["id"] and not session_user_is_admin(user):
        return templates.TemplateResponse(
            "info_objects_edit.html",
            {
                "request": request,
                "session_user": user,
                "item": None,
                "error": "Вы можете редактировать только свои информационные объекты.",
            },
            status_code=403,
        )

    return templates.TemplateResponse(
        "info_objects_edit.html",
        {
            "request": request,
            "session_user": user,
            "item": item,
            "error": None,
        },
    )


@router.post("/app/info-objects/{info_object_id}/edit", response_class=HTMLResponse)
async def app_edit_info_object_submit(
    request: Request,
    info_object_id: int,
    title: str = Form(""),
    content: str = Form(""),
    source: str = Form(""),
    author: str = Form(""),
    url: str = Form(""),
    doi: str = Form(""),
    publication_title: str = Form(""),
    publication_date_from_raw: str = Form(""),
    publication_date_to_raw: str = Form(""),
    tags_text: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    service = InfoObjectService(db)
    entity = service.find_by_id(info_object_id)

    if entity is None:
        return templates.TemplateResponse(
            "info_objects_edit.html",
            {
                "request": request,
                "session_user": user,
                "item": None,
                "error": "Информационный объект не найден",
            },
            status_code=404,
        )

    if entity.created_by != user["id"] and not session_user_is_admin(user):
        return templates.TemplateResponse(
            "info_objects_edit.html",
            {
                "request": request,
                "session_user": user,
                "item": entity,
                "error": "Вы можете редактировать только свои информационные объекты.",
            },
            status_code=403,
        )

    entity.title = title or None
    entity.content = content or None
    entity.source = source or None
    entity.author = author or None
    entity.url = url or None
    entity.doi = doi or None
    entity.publication_title = publication_title or None

    raw_from, normalized_from = normalize_partial_date(publication_date_from_raw or None, is_end=False)
    raw_to, normalized_to = normalize_partial_date(publication_date_to_raw or None, is_end=True)

    entity.publication_date_from_raw = raw_from
    entity.publication_date_to_raw = raw_to
    entity.publication_date_from = normalized_from
    entity.publication_date_to = normalized_to

    entity.tags = service.get_or_create_tags(parse_tags(tags_text))
    service.save(entity)

    return RedirectResponse(url=f"/app/info-objects/{entity.id}", status_code=303)