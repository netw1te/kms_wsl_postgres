# KMS backend для WSL + PostgreSQL

Это минимальный рабочий backend-вариант под техническое задание СУЗ.
Сейчас здесь есть:

- FastAPI backend
- PostgreSQL через Docker Compose
- Basic Auth
- тестовые пользователи `admin/admin123` и `user/user123`
- CRUD для информационных объектов
- поиск по части полей и тегам
- мягкое удаление и восстановление
- Swagger UI для визуальной проверки API

## 1. Быстрый старт в WSL

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d
export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Открыть в браузере Windows:

- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs

## 2. Тестовые данные для входа

- Администратор: `admin / admin123`
- Пользователь: `user / user123`

## 3. Что уже реализовано

### Пользователи
- `GET /api/users/is-admin?login=...`
- `GET /api/users/is-admin/{id}`
- `GET /api/users/info?login=...` — только для администратора

### Информационные объекты
- `GET /api/info-objects/`
- `GET /api/info-objects/search`
- `GET /api/info-objects/{id}`
- `POST /api/info-objects/`
- `PUT /api/info-objects/{id}`
- `PATCH /api/info-objects/{id}/soft-delete`
- `PATCH /api/info-objects/{id}/restore` — только для администратора
- `DELETE /api/info-objects/{id}` — только для администратора

## 4. Что пока не реализовано

Это именно серверная база для запуска и проверки. Полноценные формы из ТЗ пока не сделаны:

- форма принятия правил
- web-интерфейс для конечных пользователей
- вложения и изображения
- отдельная БД запросов пользователя
- администрирование доступа пользователей с периодами доступа
- импорт/экспорт всех БД

## 5. Проверка после запуска

1. Откройте `/docs`
2. Нажмите **Authorize**
3. Введите логин и пароль
4. Попробуйте `GET /api/info-objects/`
5. Затем `POST /api/info-objects/` и создайте первый объект

Пример тела:

```json
{
  "title": "Первый объект",
  "content": "Проверка запуска через WSL и PostgreSQL",
  "source": "Тест",
  "author": "Пользователь",
  "url": "https://example.com",
  "doi": "10.0000/test",
  "tags": ["wsl", "postgres", "test"]
}
```
