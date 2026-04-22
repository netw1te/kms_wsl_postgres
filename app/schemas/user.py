from typing import Optional
from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    login: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: str
