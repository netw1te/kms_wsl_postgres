from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from app.core.config import APP_TITLE, SERVER_URL


def setup_openapi(app: FastAPI) -> None:
    description = """
    Базовая документация для работы с API.

    Текущая версия предназначена для первого запуска, проверки авторизации,
    просмотра Swagger UI и тестирования базовых сценариев СУЗ.

    **Роли:**
    - `ROLE_USER` — просмотр, поиск, создание, изменение, мягкое удаление ИО.
    - `ROLE_ADMIN` — все возможности пользователя + восстановление и полное удаление.
    """

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=APP_TITLE,
            version='0.1.0',
            description=description,
            routes=app.routes,
        )
        openapi_schema['servers'] = [{'url': SERVER_URL, 'description': 'Local / WSL run'}]
        openapi_schema['components']['securitySchemes'] = {
            'basicAuth': {
                'type': 'http',
                'scheme': 'basic',
                'description': 'Введите логин и пароль пользователя',
            }
        }
        openapi_schema['security'] = [{'basicAuth': []}]
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi
