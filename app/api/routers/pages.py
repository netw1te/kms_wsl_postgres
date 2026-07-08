from typing import Dict

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=['Главная'])


@router.get('/', response_class=HTMLResponse)
async def home() -> dict[str, str]:
    return {"status": "working"}
