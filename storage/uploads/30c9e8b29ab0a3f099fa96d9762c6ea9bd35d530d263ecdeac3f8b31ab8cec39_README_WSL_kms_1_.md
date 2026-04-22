# СУЗ API — запуск в WSL2 + PostgreSQL

Это стартовая рабочая версия backend-приложения на FastAPI для проекта СУЗ.

## Что есть сейчас
- базовая авторизация по HTTP Basic;
- пользователи и роли `ROLE_USER` / `ROLE_ADMIN`;
- создание, просмотр, обновление, поиск, пометка на удаление и восстановление информационных объектов;
- работа с PostgreSQL;
- Swagger UI по адресу `http://127.0.0.1:8000/docs`.

## Тестовые пользователи
После выполнения `scripts/init_db.py` будут созданы:
- `admin / admin123`
- `user / user123`

## 1. Установить WSL и Ubuntu
В PowerShell **от имени администратора**:

```powershell
wsl --install -d Ubuntu
```

Если WSL уже установлен, проверить список дистрибутивов:

```powershell
wsl -l -v
```

Если Ubuntu установлена, открыть её можно командой:

```powershell
wsl -d Ubuntu
```

После первого запуска Ubuntu задайте имя пользователя и пароль Linux.

## 2. Обновить пакеты в Ubuntu
Внутри Ubuntu:

```bash
sudo apt update && sudo apt upgrade -y
```

## 3. Установить Python, venv и PostgreSQL

```bash
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib libpq-dev
```

Проверить PostgreSQL:

```bash
sudo service postgresql status
```

Если не запущен:

```bash
sudo service postgresql start
```

## 4. Создать базу и пользователя PostgreSQL

```bash
sudo -u postgres psql
```

Внутри `psql`:

```sql
CREATE USER kms_user WITH PASSWORD 'kms_password';
CREATE DATABASE kms_db OWNER kms_user;
GRANT ALL PRIVILEGES ON DATABASE kms_db TO kms_user;
\q
```

## 5. Скопировать проект в домашнюю папку WSL
Рекомендуется хранить проект именно **в Linux-файловой системе**, а не на диске `C:`.

Например:

```bash
mkdir -p ~/projects
cd ~/projects
```

Затем распакуйте архив проекта в `~/projects/kms_wsl_postgres`.

## 6. Создать файл `.env`
В корне проекта:

```bash
cp .env.example .env
```

## 7. Создать виртуальное окружение и установить зависимости

```bash
cd ~/projects/kms_wsl_postgres
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 8. Инициализировать таблицы и тестовых пользователей

```bash
python -m scripts.init_db
```

## 9. Запустить приложение

```bash
uvicorn app.main:app --reload
```

## 10. Открыть в браузере Windows
- Главная страница: `http://127.0.0.1:8000/`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## 11. Авторизация в Swagger
Нажмите **Authorize** и введите:
- username: `admin`
- password: `admin123`

Или:
- username: `user`
- password: `user123`

## 12. Открыть проект в VS Code через WSL
Установите Visual Studio Code в Windows и расширение **WSL**.

Из папки проекта в Ubuntu:

```bash
code .
```

VS Code откроет проект именно в WSL-среде.

## Частые проблемы

### Команда `wsl --install` не работает
Перезагрузите Windows и проверьте, включена ли виртуализация в BIOS/UEFI.

### Не подключается PostgreSQL
Проверьте, что служба запущена:

```bash
sudo service postgresql start
```

### Ошибка `password authentication failed`
Проверьте логин, пароль и строку `DATABASE_URL` в `.env`.

### `code .` не открывает VS Code
Установите расширение **WSL** и перезапустите VS Code.
