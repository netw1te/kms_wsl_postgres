from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, inspect
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
from app.api.routers.admin_import import router as admin_import_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)

    users_columns = [col["name"] for col in inspector.get_columns("users")]
    info_objects_columns = [col["name"] for col in inspector.get_columns("information_objects")]

    with engine.begin() as conn:
        if "organization" not in users_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN organization VARCHAR(255) NULL"))
        if "position" not in users_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN position VARCHAR(255) NULL"))
        if "rules_accepted_at" not in users_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN rules_accepted_at TIMESTAMP WITH TIME ZONE NULL"))
        if "registration_ip" not in users_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN registration_ip VARCHAR(45) NULL"))
        if "phone" not in users_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(20) NULL"))
        if "comment" not in users_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN comment VARCHAR(200) NULL"))
        if "access_start" not in users_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN access_start DATE NULL"))
        if "access_end" not in users_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN access_end DATE NULL"))

        if "deleted_at" not in info_objects_columns:
            conn.execute(text("ALTER TABLE information_objects ADD COLUMN deleted_at TIMESTAMP NULL"))
        if "publication_title" not in info_objects_columns:
            conn.execute(text("ALTER TABLE information_objects ADD COLUMN publication_title VARCHAR(255) NULL"))
        if "publication_date_from" not in info_objects_columns:
            conn.execute(
                text("ALTER TABLE information_objects ADD COLUMN publication_date_from TIMESTAMP WITH TIME ZONE NULL"))
        if "publication_date_to" not in info_objects_columns:
            conn.execute(
                text("ALTER TABLE information_objects ADD COLUMN publication_date_to TIMESTAMP WITH TIME ZONE NULL"))
        if "publication_date_from_raw" not in info_objects_columns:
            conn.execute(text("ALTER TABLE information_objects ADD COLUMN publication_date_from_raw VARCHAR(100) NULL"))
        if "publication_date_to_raw" not in info_objects_columns:
            conn.execute(text("ALTER TABLE information_objects ADD COLUMN publication_date_to_raw VARCHAR(100) NULL"))
        if "deleted_by" not in info_objects_columns:
            conn.execute(
                text("ALTER TABLE information_objects ADD COLUMN deleted_by INTEGER REFERENCES users(id) NULL"))
        if "replacement_info_id" not in info_objects_columns:
            conn.execute(text(
                "ALTER TABLE information_objects ADD COLUMN replacement_info_id INTEGER REFERENCES information_objects(info_id) NULL"))

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
app.include_router(admin_import_router)
from app.api.routers.complex_search import router as complex_search_router

app.include_router(complex_search_router)