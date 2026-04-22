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

    publication_title: Optional[str] = None
    publication_date_from_raw: Optional[str] = None
    publication_date_to_raw: Optional[str] = None

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

    tags: List[str] = Field(default_factory=list)


class InfoObjectResponse(BaseModel):
    id: int
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None

    publication_title: Optional[str] = None
    publication_date_from_raw: Optional[str] = None
    publication_date_to_raw: Optional[str] = None
    publication_date_from: Optional[datetime] = None
    publication_date_to: Optional[datetime] = None

    tags: List[str] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None

    deletion_flag: bool = False
    deletion_reason: Optional[str] = None
    deleted_by: Optional[int] = None
    replacement_info_object_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)