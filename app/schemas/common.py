from typing import Any
from pydantic import BaseModel


class PageResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    size: int
    pages: int
