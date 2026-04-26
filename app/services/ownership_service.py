from fastapi import HTTPException, status

from app.auth import CurrentUser
from app.models.info_object import InfoObject


def ensure_can_modify_info_object(current_user: CurrentUser, info_object: InfoObject) -> None:
    if current_user.role == "ROLE_ADMIN":
        return

    if info_object.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете изменять только свои информационные объекты.",
        )