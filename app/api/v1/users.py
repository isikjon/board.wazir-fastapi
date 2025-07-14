from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas, services
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.User])
def read_users(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_admin),
) -> Any:
    users = services.user.get_multi(db, skip=skip, limit=limit)
    return users


@router.get("/chat-contacts", response_model=List[schemas.User])
def get_chat_contacts(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Получить список пользователей для чата (все пользователи кроме текущего)"""
    users = db.query(models.User).filter(models.User.id != current_user.id).all()
    return users


@router.get("/me", response_model=schemas.User)
def read_user_me(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    return current_user


@router.put("/me", response_model=schemas.User)
def update_user_me(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    user = services.user.update(db, db_obj=current_user, obj_in=user_in)
    return user


@router.get("/{user_id}", response_model=schemas.User)
def read_user_by_id(
    user_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    user = services.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Пользователь не найден",
        )
    if user.id != current_user.id and not services.user.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра информации о другом пользователе",
        )
    return user


@router.put("/{user_id}", response_model=schemas.User)
def update_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    user_in: schemas.UserUpdate,
    current_user: models.User = Depends(deps.get_current_active_admin),
) -> Any:
    user = services.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Пользователь не найден",
        )
    user = services.user.update(db, db_obj=user, obj_in=user_in)
    return user


@router.put("/{user_id}/activate", response_model=schemas.User)
def activate_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    current_user: models.User = Depends(deps.get_current_active_admin),
) -> Any:
    user = services.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Пользователь не найден",
        )
    
    user_update = {"is_active": True}
    user = services.user.update(db, db_obj=user, obj_in=user_update)
    return user


@router.put("/{user_id}/deactivate", response_model=schemas.User)
def deactivate_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    current_user: models.User = Depends(deps.get_current_active_admin),
) -> Any:
    user = services.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Пользователь не найден",
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Невозможно деактивировать свою учетную запись",
        )
    
    user_update = {"is_active": False}
    user = services.user.update(db, db_obj=user, obj_in=user_update)
    return user 