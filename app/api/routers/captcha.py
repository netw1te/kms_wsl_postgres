import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.core.captcha import generate_captcha_text, generate_captcha_image
from app.database import get_db
from app.models.captcha import Captcha

router = APIRouter(prefix="/captcha", tags=["Captcha"])


@router.get("/image")
async def get_captcha(response: Response, db: Session = Depends(get_db)):
    session_id = str(uuid.uuid4())
    text = generate_captcha_text(5)
    expires_at = datetime.now() + timedelta(minutes=10)

    captcha = Captcha(
        session_id=session_id,
        text=text,
        expires_at=expires_at,
        used=0
    )
    db.add(captcha)
    db.commit()

    response.set_cookie(key="captcha_id", value=session_id, httponly=True, max_age=600)

    return StreamingResponse(generate_captcha_image(text), media_type="image/png")


@router.post("/check")
async def check_captcha(session_id: str, code: str, db: Session = Depends(get_db)):
    record = db.query(Captcha).filter(
        Captcha.session_id == session_id,
        Captcha.expires_at > datetime.now(),
        Captcha.used == 0
    ).first()

    if not record:
        return {"ok": False, "error": "Капча устарела, обновите страницу"}

    if record.text.upper() != code.strip().upper():
        return {"ok": False, "error": "Неверный код"}

    record.used = 1
    db.commit()
    return {"ok": True}