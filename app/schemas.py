from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class InfoObjectCreate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    publication_title: Optional[str] = None
    publication_date_from: Optional[datetime] = None
    publication_date_to: Optional[datetime] = None
    publication_date_from_raw: Optional[str] = None
    publication_date_to_raw: Optional[str] = None


class InfoObjectUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    publication_title: Optional[str] = None
    publication_date_from: Optional[datetime] = None
    publication_date_to: Optional[datetime] = None
    publication_date_from_raw: Optional[str] = None
    publication_date_to_raw: Optional[str] = None


class InfoObjectResponse(BaseModel):
    id: int
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    deletion_flag: bool = False
    deletion_reason: Optional[str] = None
    publication_title: Optional[str] = None
    publication_date_from: Optional[datetime] = None
    publication_date_to: Optional[datetime] = None
    publication_date_from_raw: Optional[str] = None
    publication_date_to_raw: Optional[str] = None
    deleted_by: Optional[int] = None
    replacement_info_id: Optional[int] = None
    replacement_info_object_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PageResponse(BaseModel):
    items: List[InfoObjectResponse]
    total: int
    page: int
    size: int
    pages: int


class UserCreateByAdmin(BaseModel):
    login: str
    password: str
    email: Optional[str] = None
    role: str
    phone: Optional[str] = None
    comment: Optional[str] = None
    access_start: Optional[date] = None
    access_end: Optional[date] = None
    organization: Optional[str] = None
    position: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    login: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: str
    access_start: Optional[date] = None
    access_end: Optional[date] = None
    is_user_admin: bool
    is_data_admin: bool
    is_super_admin: bool
    organization: Optional[str] = None
    position: Optional[str] = None
    rules_accepted_at: Optional[datetime] = None
    registration_ip: Optional[str] = None
    phone: Optional[str] = None
    comment: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)