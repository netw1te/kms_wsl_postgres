import os

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def setup_openapi(app: FastAPI) -> None:
    server_url = os.getenv("SERVER_URL", "http://127.0.0.1:8000")
    description = """
    Базовая документация API для минимального backend-варианта СУЗ.

    Сейчас в проекте реализована серверная часть для пользователей и информационных объектов.
    Полноценные экранные формы из технического задания пока не реализованы: сначала поднимаем API,
    проверяем авторизацию, CRUD, поиск и мягкое удаление, затем добавляем web-интерфейс.
    """

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title="KMS API",
            version="0.1.0",
            description=description,
            routes=app.routes,
        )
        openapi_schema["servers"] = [
            {
                "url": server_url,
                "description": "Local development server",
            }
        ]
        openapi_schema.setdefault("components", {})["securitySchemes"] = {
            "basicAuth": {
                "type": "http",
                "scheme": "basic",
                "description": "Используйте логин и пароль тестового пользователя или администратора.",
            }
        }
        openapi_schema["security"] = [{"basicAuth": []}]
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi
