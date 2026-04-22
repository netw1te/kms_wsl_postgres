from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models.info_object import InfoObject, Tag


router = APIRouter(prefix="/tags", tags=["Метки"])


class TagReplaceRequest(BaseModel):
    old_tag: str
    new_tag: str
    scope: str = "mine"  # mine | all


class TagDeleteRequest(BaseModel):
    tag: str
    scope: str = "mine"  # mine | all


class TagSearchResponse(BaseModel):
    items: list[str]


def ensure_scope_allowed(scope: str, current_user: CurrentUser):
    if scope == "all" and not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Изменение меток для всех ИО доступно только администратору.",
        )

def cleanup_orphan_tag(db: Session, tag: Tag | None) -> None:
    if tag is None:
        return
    db.refresh(tag)
    if not tag.info_objects:
        db.delete(tag)

@router.get("", response_model=TagSearchResponse)
async def search_tags(
    q: str = "",
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    query = (
        db.query(Tag)
        .filter(Tag.info_objects.any())
    )

    if q.strip():
        query = query.filter(Tag.name.ilike(f"%{q.strip()}%"))

    items = query.order_by(Tag.name.asc()).limit(50).all()
    return TagSearchResponse(items=[item.name for item in items])

@router.post("/replace")
async def replace_tag(
    payload: TagReplaceRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    ensure_scope_allowed(payload.scope, current_user)

    old_tag_name = payload.old_tag.strip()
    new_tag_name = payload.new_tag.strip()

    if not old_tag_name or not new_tag_name:
        raise HTTPException(status_code=400, detail="old_tag и new_tag обязательны.")

    old_tag = db.query(Tag).filter(Tag.name == old_tag_name).first()
    if old_tag is None:
        raise HTTPException(status_code=404, detail="Исходная метка не найдена.")

    new_tag = db.query(Tag).filter(Tag.name == new_tag_name).first()
    if new_tag is None:
        new_tag = Tag(name=new_tag_name)
        db.add(new_tag)
        db.flush()

    query = db.query(InfoObject).filter(InfoObject.tags.any(Tag.id == old_tag.id))
    if payload.scope == "mine":
        query = query.filter(InfoObject.created_by == current_user.id)

    info_objects = query.all()
    changed = 0

    for item in info_objects:
        tag_ids = {tag.id for tag in item.tags}
        if old_tag.id in tag_ids and new_tag.id not in tag_ids:
            item.tags.append(new_tag)
        item.tags = [tag for tag in item.tags if tag.id != old_tag.id]
        changed += 1

    cleanup_orphan_tag(db, old_tag)
    db.commit()
    return {"changed": changed, "old_tag": old_tag_name, "new_tag": new_tag_name}


@router.post("/delete")
async def delete_tag_from_objects(
    payload: TagDeleteRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    ensure_scope_allowed(payload.scope, current_user)

    tag_name = payload.tag.strip()
    if not tag_name:
        raise HTTPException(status_code=400, detail="tag обязателен.")

    tag = db.query(Tag).filter(Tag.name == tag_name).first()
    if tag is None:
        raise HTTPException(status_code=404, detail="Метка не найдена.")

    query = db.query(InfoObject).filter(InfoObject.tags.any(Tag.id == tag.id))
    if payload.scope == "mine":
        query = query.filter(InfoObject.created_by == current_user.id)

    info_objects = query.all()
    changed = 0

    for item in info_objects:
        before = len(item.tags)
        item.tags = [t for t in item.tags if t.id != tag.id]
        if len(item.tags) != before:
            changed += 1

    cleanup_orphan_tag(db, tag)
    db.commit()
    return {"changed": changed, "deleted_tag": tag_name}