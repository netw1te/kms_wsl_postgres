from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models.user_agreement import UserAgreement


router = APIRouter(prefix="/agreements", tags=["Согласия"])


class AgreementStatusResponse(BaseModel):
    accepted: bool
    full_name: str | None = None
    job_title: str | None = None
    organization: str | None = None


class AgreementCreateRequest(BaseModel):
    full_name: str
    job_title: str
    organization: str
    accepted_rules: bool
    accepted_personal_data: bool


@router.get("/me", response_model=AgreementStatusResponse)
async def get_my_agreement(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    item = db.query(UserAgreement).filter(UserAgreement.user_id == current_user.id).first()
    if not item:
        return AgreementStatusResponse(accepted=False)

    return AgreementStatusResponse(
        accepted=bool(item.accepted_rules and item.accepted_personal_data),
        full_name=item.full_name,
        job_title=item.job_title,
        organization=item.organization,
    )


@router.post("/me", response_model=AgreementStatusResponse)
async def accept_my_agreement(
    payload: AgreementCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not payload.accepted_rules or not payload.accepted_personal_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо принять оба согласия.",
        )

    item = db.query(UserAgreement).filter(UserAgreement.user_id == current_user.id).first()
    if item is None:
        item = UserAgreement(user_id=current_user.id)
        db.add(item)

    item.full_name = payload.full_name.strip()
    item.job_title = payload.job_title.strip()
    item.organization = payload.organization.strip()
    item.accepted_rules = True
    item.accepted_personal_data = True
    item.accepted_ip = request.client.host if request.client else None

    db.commit()
    db.refresh(item)

    return AgreementStatusResponse(
        accepted=True,
        full_name=item.full_name,
        job_title=item.job_title,
        organization=item.organization,
    )