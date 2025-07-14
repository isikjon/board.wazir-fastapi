from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from app.services.base import CRUDBase
from app.models.message import Message as AppMessage
from app.schemas.message import MessageCreate


class CRUDMessage(CRUDBase[AppMessage, MessageCreate, Any]):
    def create_with_sender(
        self, db: Session, *, obj_in: MessageCreate, sender_id: int
    ) -> AppMessage:
        obj_in_data = obj_in.dict()
        db_obj = AppMessage(**obj_in_data, sender_id=sender_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_user_messages(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[AppMessage]:
        return (
            db.query(AppMessage)
            .filter(
                (AppMessage.sender_id == user_id) | (AppMessage.recipient_id == user_id)
            )
            .order_by(AppMessage.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_conversation(
        self, db: Session, *, user_id: int, other_user_id: int, skip: int = 0, limit: int = 100
    ) -> List[AppMessage]:
        return (
            db.query(AppMessage)
            .filter(
                ((AppMessage.sender_id == user_id) & (AppMessage.recipient_id == other_user_id)) |
                ((AppMessage.sender_id == other_user_id) & (AppMessage.recipient_id == user_id))
            )
            .order_by(AppMessage.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )


# Создаем экземпляр CRUD для сообщений
message = CRUDMessage(AppMessage)