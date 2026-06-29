from datetime import datetime
from typing import Optional
import re
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlalchemy import text, Column, String
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.auth import CurrentUser, PasswordEncoder, get_current_user, require_user_admin
from app.database import get_db, Base
from app.models.user import User
from app.models.user_agreement import UserAgreement

router = APIRouter(prefix="/users", tags=["Пользователи"])


class SystemSetting(Base):
    __tablename__ = "system_settings"
    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=False)


class RulesLinkSettingsRequest(BaseModel):
    rules_url: str


class UserResponse(BaseModel):
    id: int
    login: str
    full_name: str | None = None
    email: str | None = None
    is_user_admin: bool = False
    is_data_admin: bool = False
    is_super_admin: bool = False
    organization: str | None = None
    position: str | None = None
    phone: str | None = None
    comment: str | None = None
    access_start: Optional[datetime] = None
    access_end: Optional[datetime] = None
    rules_accepted: bool = False
    rules_accepted_at: Optional[datetime] = None


class UserCreateByAdminRequest(BaseModel):
    login: str
    password: str
    full_name: str | None = None
    email: str | None = None
    is_user_admin: bool = False
    is_data_admin: bool = False
    is_super_admin: bool = False
    organization: str | None = None
    position: str | None = None
    phone: str | None = None
    comment: str | None = None
    access_start: str | None = None
    access_end: str | None = None

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v):
        if not v:
            return None
        import re
        pattern = r"^\+?[\d\s\-()]{7,18}$"
        if not re.match(pattern, str(v)):
            raise HTTPException(status_code=400, detail="Некорректный формат номера телефона")
        return str(v)


class UserUpdateRequest(BaseModel):
    login: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    access_start: Optional[str] = None
    access_end: Optional[str] = None
    is_user_admin: Optional[bool] = None
    is_data_admin: Optional[bool] = None
    is_super_admin: Optional[bool] = None
    organization: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    comment: Optional[str] = None

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v):
        if not v:
            return None
        import re
        pattern = r"^\+?[\d\s\-()]{7,18}$"
        if not re.match(pattern, str(v)):
            raise HTTPException(status_code=400, detail="Некорректный формат номера телефона")
        return str(v)


class UserAccessDatesUpdateRequest(BaseModel):
    access_start_date: Optional[str] = None
    access_end_date: Optional[str] = None


def serialize_user(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        login=user.login,
        full_name=user.full_name,
        email=user.email,
        is_user_admin=bool(getattr(user, "is_user_admin", False)),
        is_data_admin=bool(getattr(user, "is_data_admin", False)),
        is_super_admin=bool(getattr(user, "is_super_admin", False)),
        organization=getattr(user, "organization", None),
        position=getattr(user, "position", None),
        phone=getattr(user, "phone", None),
        comment=getattr(user, "comment", None),
        access_start=getattr(user, "access_start", None),
        access_end=getattr(user, "access_end", None),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser = Depends(get_current_user)):
    return serialize_user(current_user)


@router.get("/info", response_model=UserResponse)
async def get_info(login: str = Query(...), db: Session = Depends(get_db),
                   current_admin: CurrentUser = Depends(require_user_admin)):
    user = db.query(User).filter(User.login == login).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize_user(user)


@router.get("", response_model=list[UserResponse])
async def get_all_users(db: Session = Depends(get_db), current_admin: CurrentUser = Depends(require_user_admin)):
    users = db.query(User).order_by(User.id.asc()).all()
    from app.models.user_agreement import UserAgreement
    agreements = {a.user_id: a for a in db.query(UserAgreement).all()}

    result = []
    for u in users:
        res = serialize_user(u)
        agr = agreements.get(u.id)
        if agr:
            res.rules_accepted = bool(agr.accepted_rules)
            res.rules_accepted_at = agr.accepted_at
        result.append(res)
    return result


@router.post("/admin-create", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_by_admin(payload: UserCreateByAdminRequest, db: Session = Depends(get_db),
                               current_admin: CurrentUser = Depends(require_user_admin)):
    if current_admin.is_user_admin and not current_admin.is_super_admin:
        if payload.is_data_admin or payload.is_super_admin:
            raise HTTPException(status_code=403, detail="У вас нет прав на назначение данных ролей.")
    login = payload.login.strip()
    password = payload.password.strip()
    if not login or not password:
        raise HTTPException(status_code=400, detail="Логин и пароль обязательны.")
    if db.query(User).filter(User.login == login).first():
        raise HTTPException(status_code=409, detail="Пользователь с таким логином уже существует.")
    user = User(
        login=login,
        password=PasswordEncoder.hash(password),
        full_name=payload.full_name.strip() if payload.full_name else None,
        email=payload.email.strip() if payload.email else None,
        is_user_admin=payload.is_user_admin,
        is_data_admin=payload.is_data_admin,
        is_super_admin=payload.is_super_admin,
        organization=payload.organization,
        position=payload.position,
        phone=payload.phone,
        comment=payload.comment,
        access_start=datetime.fromisoformat(payload.access_start) if payload.access_start else None,
        access_end=datetime.fromisoformat(payload.access_end) if payload.access_end else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return serialize_user(user)


@router.get("/rules-link")
async def get_rules_link(db: Session = Depends(get_db)):
    setting = db.query(SystemSetting).filter(SystemSetting.key == "rules_url").first()
    if not setting:
        return {"rules_url": "https://example.com/rules"}
    return {"rules_url": setting.value}


@router.put("/rules-link")
async def update_rules_link(
    payload: RulesLinkSettingsRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Только суперадминистратор может менять ссылку")

    setting = db.query(SystemSetting).filter(SystemSetting.key == "rules_url").first()
    if not setting:
        setting = SystemSetting(key="rules_url", value=payload.rules_url)
        db.add(setting)
    else:
        setting.value = payload.rules_url

    from app.models.user_agreement import UserAgreement
    db.query(UserAgreement).update({
        UserAgreement.accepted_rules: False,
        UserAgreement.accepted_at: datetime(1970, 1, 1)
    })

    db.commit()
    return {"rules_url": payload.rules_url}


@router.put("/{user_id}/access-dates", response_model=UserResponse)
async def update_user_access_dates(
    user_id: int,
    payload: UserAccessDatesUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: CurrentUser = Depends(require_user_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.access_start_date is not None:
        user.access_start = datetime.fromisoformat(payload.access_start_date) if payload.access_start_date else None
    if payload.access_end_date is not None:
        user.access_end = datetime.fromisoformat(payload.access_end_date) if payload.access_end_date else None

    db.commit()
    db.refresh(user)
    return serialize_user(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, payload: UserUpdateRequest, db: Session = Depends(get_db),
                      current_admin: CurrentUser = Depends(require_user_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = payload.model_dump(exclude_unset=True)
    if "login" in update_data and payload.login:
        user.login = payload.login.strip()
    for field in ["full_name", "email", "organization", "position", "phone", "comment"]:
        if field in update_data:
            val = update_data[field]
            setattr(user, field, val.strip() if isinstance(val, str) else val)
    if "access_start" in update_data:
        user.access_start = datetime.fromisoformat(payload.access_start) if payload.access_start else None
    if "access_end" in update_data:
        user.access_end = datetime.fromisoformat(payload.access_end) if payload.access_end else None
    if "is_user_admin" in update_data:
        user.is_user_admin = payload.is_user_admin
    if "is_data_admin" in update_data:
        user.is_data_admin = payload.is_data_admin
    if "is_super_admin" in update_data:
        user.is_super_admin = payload.is_super_admin
    db.commit()
    db.refresh(user)
    return serialize_user(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Session = Depends(get_db),
                      current_admin: CurrentUser = Depends(require_user_admin)):
    if current_admin.id == user_id:
        raise HTTPException(status_code=400, detail="Нельзя удалить текущего пользователя.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        db.execute(text("DELETE FROM user_agreements WHERE user_id = :user_id"), {"user_id": user_id})
        db.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": user_id})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Удаление остановлено, присутствуют связи с данными.")


@router.post("/{user_id}/block")
async def block_user(user_id: int, db: Session = Depends(get_db),
                     current_admin: CurrentUser = Depends(require_user_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.access_end = datetime(1970, 1, 1)
    db.commit()
    return {"message": "User blocked", "user_id": user_id}


@router.post("/{user_id}/unblock")
async def unblock_user(user_id: int, db: Session = Depends(get_db),
                       current_admin: CurrentUser = Depends(require_user_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.access_end = None
    db.commit()
    return {"message": "User unblocked", "user_id": user_id}