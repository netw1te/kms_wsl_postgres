from app.core.security import password_encoder
from app.database import Base, SessionLocal, engine
from app.models.info_object import InfoObject, Tag  # noqa: F401
from app.models.user import User


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.login == 'admin').first()
        user = db.query(User).filter(User.login == 'user').first()

        if not admin:
            admin = User(
                login='admin',
                password=password_encoder.encode('admin123'),
                full_name='Администратор',
                email='admin@example.com',
                role='ROLE_ADMIN',
            )
            db.add(admin)

        if not user:
            user = User(
                login='user',
                password=password_encoder.encode('user123'),
                full_name='Обычный пользователь',
                email='user@example.com',
                role='ROLE_USER',
            )
            db.add(user)

        db.commit()
        print('База инициализирована успешно.')
        print('Созданы пользователи: admin/admin123 и user/user123 (если их не было).')
    finally:
        db.close()


if __name__ == '__main__':
    main()
