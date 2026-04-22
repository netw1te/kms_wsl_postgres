import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+psycopg2://kms_user:kms_password@localhost:5432/kms_db'
)

SERVER_URL = os.getenv('SERVER_URL', 'http://127.0.0.1:8000')
APP_TITLE = os.getenv('APP_TITLE', 'Система управления знаниями API')
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-change-me')
