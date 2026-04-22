from datetime import datetime
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


class InfoObjectUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


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

    model_config = ConfigDict(from_attributes=True)


class PageResponse(BaseModel):
    items: List[InfoObjectResponse]
    total: int
    page: int
    size: int
    pages: int


class UserResponse(BaseModel):
    id: int
    login: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: str

    model_config = ConfigDict(from_attributes=True)
