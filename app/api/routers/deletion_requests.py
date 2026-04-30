from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user, require_admin
from app.database import get_db
from app.models.info_object import InfoObject
from app.models.info_object_deletion_request import InfoObjectDeletionRequest


router = APIRouter(prefix="/deletion-requests", tags=["Запросы на удаление"])


class DeletionRequestCreate(BaseModel):
    reason: str | None = None
    replacement_info_object_id: int | None = None


class DeletionRequestResponse(BaseModel):
    id: int
    info_object_id: int
    requested_by: int
    reason: str | None = None
    replacement_info_object_id: int | None = None
    status: str
    created_at: datetime


class DeletionRequestStatusResponse(BaseModel):
    exists: bool
    id: int | None = None
    status: str | None = None
    reason: str | None = None
    replacement_info_object_id: int | None = None


def serialize_request(item: InfoObjectDeletionRequest) -> DeletionRequestResponse:
    return DeletionRequestResponse(
        id=item.id,
        info_object_id=item.info_object_id,
        requested_by=item.requested_by,
        reason=item.reason,
        replacement_info_object_id=item.replacement_info_object_id,
        status=item.status,
        created_at=item.created_at,
    )


@router.post(
    "/info-objects/{info_object_id}",
    response_model=DeletionRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_deletion_request(
    info_object_id: int,
    payload: DeletionRequestCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    info_object = db.query(InfoObject).filter(InfoObject.id == info_object_id).first()
    if info_object is None:
        raise HTTPException(status_code=404, detail="InfoObject not found")

    if current_user.role != "ROLE_ADMIN" and info_object.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Можно запрашивать удаление только своих ИО.",
        )

    if info_object.deletion_flag:
        raise HTTPException(
            status_code=409,
            detail="ИО уже помечен как удалённый.",
        )

    existing = (
        db.query(InfoObjectDeletionRequest)
        .filter(
            InfoObjectDeletionRequest.info_object_id == info_object_id,
            InfoObjectDeletionRequest.status == "pending",
        )
        .order_by(InfoObjectDeletionRequest.created_at.desc())
        .first()
    )

    if existing:
        return serialize_request(existing)

    item = InfoObjectDeletionRequest(
        info_object_id=info_object_id,
        requested_by=current_user.id,
        reason=payload.reason.strip() if payload.reason else None,
        replacement_info_object_id=payload.replacement_info_object_id,
        status="pending",
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return serialize_request(item)


@router.get("", response_model=list[DeletionRequestResponse])
async def list_deletion_requests(
    db: Session = Depends(get_db),
    current_admin: CurrentUser = Depends(require_admin),
):
    items = (
        db.query(InfoObjectDeletionRequest)
        .filter(InfoObjectDeletionRequest.status == "pending")
        .order_by(InfoObjectDeletionRequest.created_at.desc())
        .all()
    )

    result: list[InfoObjectDeletionRequest] = []
    seen_info_object_ids: set[int] = set()

    for item in items:
        if item.info_object_id in seen_info_object_ids:
            continue

        seen_info_object_ids.add(item.info_object_id)
        result.append(item)

    return [serialize_request(item) for item in result]


@router.post("/{request_id}/approve-delete", status_code=status.HTTP_204_NO_CONTENT)
async def approve_delete_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_admin: CurrentUser = Depends(require_admin),
):
    item = (
        db.query(InfoObjectDeletionRequest)
        .filter(InfoObjectDeletionRequest.id == request_id)
        .first()
    )

    if item is None:
        raise HTTPException(status_code=404, detail="Deletion request not found")

    if item.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Запрос на удаление уже обработан.",
        )

    info_object = db.query(InfoObject).filter(InfoObject.id == item.info_object_id).first()
    if info_object is None:
        raise HTTPException(status_code=404, detail="InfoObject not found")

    info_object.deletion_flag = True
    info_object.deleted_at = datetime.utcnow()
    info_object.deletion_reason = item.reason
    info_object.replacement_info_object_id = item.replacement_info_object_id

    if hasattr(info_object, "deleted_by"):
        info_object.deleted_by = current_admin.id

    item.status = "approved"
    item.reviewed_by = current_admin.id
    item.reviewed_at = datetime.utcnow()

    db.add(info_object)
    db.add(item)
    db.commit()


@router.get(
    "/info-objects/{info_object_id}/status",
    response_model=DeletionRequestStatusResponse,
)
async def get_deletion_request_status(
    info_object_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    info_object = db.query(InfoObject).filter(InfoObject.id == info_object_id).first()
    if info_object is None:
        raise HTTPException(status_code=404, detail="InfoObject not found")

    if current_user.role != "ROLE_ADMIN" and info_object.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if info_object.deletion_flag:
        approved_request = (
            db.query(InfoObjectDeletionRequest)
            .filter(
                InfoObjectDeletionRequest.info_object_id == info_object_id,
                InfoObjectDeletionRequest.status == "approved",
            )
            .order_by(InfoObjectDeletionRequest.created_at.desc())
            .first()
        )

        return DeletionRequestStatusResponse(
            exists=True,
            id=approved_request.id if approved_request else None,
            status="approved",
            reason=(
                approved_request.reason
                if approved_request and approved_request.reason
                else info_object.deletion_reason
            ),
            replacement_info_object_id=(
                approved_request.replacement_info_object_id
                if approved_request and approved_request.replacement_info_object_id
                else info_object.replacement_info_object_id
            ),
        )

    pending_request = (
        db.query(InfoObjectDeletionRequest)
        .filter(
            InfoObjectDeletionRequest.info_object_id == info_object_id,
            InfoObjectDeletionRequest.status == "pending",
        )
        .order_by(InfoObjectDeletionRequest.created_at.desc())
        .first()
    )

    if pending_request is None:
        return DeletionRequestStatusResponse(exists=False)

    return DeletionRequestStatusResponse(
        exists=True,
        id=pending_request.id,
        status=pending_request.status,
        reason=pending_request.reason,
        replacement_info_object_id=pending_request.replacement_info_object_id,
    )