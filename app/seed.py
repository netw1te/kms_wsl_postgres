from sqlalchemy.orm import Session

from app.auth import PasswordEncoder
from app.models.user import User


def seed_users(db: Session) -> None:
    admin = db.query(User).filter(User.login == "admin").first()
    if admin is None:
        db.add(
            User(
                login="admin",
                password=PasswordEncoder.encode("admin123"),
                full_name="Local Admin",
                email="admin@example.com",
                role="ROLE_ADMIN",
            )
        )

    user = db.query(User).filter(User.login == "user").first()
    if user is None:
        db.add(
            User(
                login="user",
                password=PasswordEncoder.encode("user123"),
                full_name="Local User",
                email="user@example.com",
                role="ROLE_USER",
            )
        )

    db.commit()