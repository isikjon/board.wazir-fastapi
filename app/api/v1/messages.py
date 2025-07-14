from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas, services
from app.api import deps
from app.schemas.message import Message as AppMessageSchema

router = APIRouter()


@router.get("/", response_model=List[AppMessageSchema])
def read_messages(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    messages = services.message.get_user_messages(
        db=db, user_id=current_user.id, skip=skip, limit=limit
    )
    return messages


@router.post("/", response_model=AppMessageSchema)
def create_message(
    *,
    db: Session = Depends(deps.get_db),
    message_in: schemas.MessageCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    recipient = services.user.get(db=db, id=message_in.recipient_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Получатель не найден")
    
    message = services.message.create_with_sender(
        db=db, obj_in=message_in, sender_id=current_user.id
    )
    return message


@router.get("/conversation/{user_id}", response_model=List[AppMessageSchema])
def read_conversation(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    other_user = services.user.get(db=db, id=user_id)
    if not other_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    messages = services.message.get_conversation(
        db=db, user_id=current_user.id, other_user_id=user_id, skip=skip, limit=limit
    )
    return messages 