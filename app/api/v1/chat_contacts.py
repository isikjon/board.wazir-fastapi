from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.UserInDBBase])
def get_users_for_chat(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Получить список всех пользователей для чата, кроме текущего пользователя.
    """
    users = db.query(models.User).filter(
        models.User.id != current_user.id,
        models.User.is_active == True
    ).all()
    return users
