from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=['Главная'])


@router.get('/', response_class=HTMLResponse)
async def home() -> str:
    return """
    <html>
      <head>
        <meta charset=\"utf-8\" />
        <title>СУЗ API</title>
        <style>
          body { font-family: Arial, sans-serif; max-width: 860px; margin: 40px auto; line-height: 1.5; }
          .box { padding: 20px; border: 1px solid #ddd; border-radius: 12px; }
          code { background: #f5f5f5; padding: 2px 6px; border-radius: 6px; }
          a { text-decoration: none; }
        </style>
      </head>
      <body>
        <div class=\"box\">
          <h1>Система управления знаниями — API</h1>
          <p>Сервер запущен успешно.</p>
          <p>Откройте <a href=\"/docs\">Swagger UI</a> для визуальной проверки API.</p>
          <p>Также доступен <a href=\"/redoc\">ReDoc</a>.</p>
          <p>Тестовые логины после инициализации базы:</p>
          <ul>
            <li><code>admin / admin123</code></li>
            <li><code>user / user123</code></li>
          </ul>
        </div>
      </body>
    </html>
    """
