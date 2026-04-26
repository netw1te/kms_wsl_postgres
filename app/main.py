from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

from app.api.routers.files import router as files_router
from app.api.routers.info_objects import router as info_objects_router
from app.api.routers.pages import router as pages_router
from app.api.routers.search_query_router import router as search_query_router
from app.api.routers.users import router as users_router
from app.api.routers.web import router as web_router
from app.core.config import APP_TITLE, SECRET_KEY
from app.core.openapi import setup_openapi
from app.database import Base, SessionLocal, engine
from app.api.routers.tags import router as tags_router
from app.api.routers.user_agreements import router as user_agreements_router
from app.api.routers.deletion_requests import router as deletion_requests_router
from app.api.routers.captcha import router as captcha_router
from app.api.routers.admin_export import router as admin_export_router
from app.services.info_object_service import InfoObjectService

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                ALTER TABLE information_objects
                ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL
                """
            )
        )

    db = SessionLocal()
    try:
        InfoObjectService(db).purge_deleted_older_than(days=7)
    finally:
        db.close()

    yield


app = FastAPI(title=APP_TITLE, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://192.168.0.15:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, same_site="lax")

setup_openapi(app)

app.include_router(pages_router)
app.include_router(info_objects_router)
app.include_router(users_router)
app.include_router(search_query_router)
app.include_router(files_router)
app.include_router(web_router)
app.include_router(tags_router)
app.include_router(user_agreements_router)
app.include_router(deletion_requests_router)
app.include_router(captcha_router)
app.include_router(admin_export_router)
