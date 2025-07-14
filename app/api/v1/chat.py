from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from typing import List, Dict, Any
from app.api import deps
from app.models.chat import AppChatModel, AppChatMessageModel
from app.models.user import User
from app.schemas.chat import Message, MessageCreate, MessageRead, ChatPreview
from datetime import datetime

router = APIRouter()


@router.get("/", response_model=List[ChatPreview])
def get_user_chats(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    user_id = current_user.id
    
    # Находим все чаты текущего пользователя
    chats = db.query(AppChatModel).filter(
        or_(
            AppChatModel.user1_id == user_id,
            AppChatModel.user2_id == user_id
        )
    ).all()
    
    chat_previews = []
    for chat in chats:
        # Определяем второго участника чата
        other_user_id = chat.user2_id if chat.user1_id == user_id else chat.user1_id
        other_user = db.query(User).filter(User.id == other_user_id).first()
        
        if not other_user:
            continue
        
        # Получаем последнее сообщение
        last_message = db.query(AppChatMessageModel).filter(
            AppChatMessageModel.chat_id == chat.id
        ).order_by(AppChatMessageModel.created_at.desc()).first()
        
        # Считаем непрочитанные сообщения
        unread_count = db.query(func.count(AppChatMessageModel.id)).filter(
            AppChatMessageModel.chat_id == chat.id,
            AppChatMessageModel.sender_id == other_user_id,
            AppChatMessageModel.is_read == False
        ).scalar()
        
        chat_previews.append({
            "user": other_user,
            "last_message": last_message,
            "unread_count": unread_count
        })
    
    return chat_previews


@router.get("/messages/{user_id}", response_model=List[Message])
def get_chat_messages(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    # Находим или создаем чат между пользователями
    chat = db.query(AppChatModel).filter(
        or_(
            and_(AppChatModel.user1_id == current_user.id, AppChatModel.user2_id == user_id),
            and_(AppChatModel.user1_id == user_id, AppChatModel.user2_id == current_user.id)
        )
    ).first()
    
    if not chat:
        # Если чата нет, возвращаем пустой список
        return []
    
    # Получаем все сообщения чата
    messages = db.query(AppChatMessageModel).filter(
        AppChatMessageModel.chat_id == chat.id
    ).order_by(AppChatMessageModel.created_at).all()
    
    return messages


@router.post("/messages", response_model=Message)
def create_message(
    message: MessageCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    receiver = db.query(User).filter(User.id == message.receiver_id).first()
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Получатель не найден"
        )
    
    # Находим или создаем чат между пользователями
    chat = db.query(AppChatModel).filter(
        or_(
            and_(AppChatModel.user1_id == current_user.id, AppChatModel.user2_id == message.receiver_id),
            and_(AppChatModel.user1_id == message.receiver_id, AppChatModel.user2_id == current_user.id)
        )
    ).first()
    
    if not chat:
        # Создаем новый чат
        chat = AppChatModel(
            user1_id=current_user.id,
            user2_id=message.receiver_id
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
    
    # Создаем сообщение
    db_message = AppChatMessageModel(
        chat_id=chat.id,
        sender_id=current_user.id,
        content=message.content,
        is_read=False
    )
    
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    return db_message


@router.post("/messages/read", status_code=status.HTTP_200_OK)
def mark_message_as_read(
    data: MessageRead,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    # Находим сообщение по ID
    message = db.query(AppChatMessageModel).filter(
        AppChatMessageModel.id == data.message_id
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сообщение не найдено"
        )
    
    # Проверяем, что пользователь имеет право отметить сообщение как прочитанное
    chat = db.query(AppChatModel).filter(AppChatModel.id == message.chat_id).first()
    if not chat or (chat.user1_id != current_user.id and chat.user2_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к данному сообщению"
        )
    
    # Отмечаем сообщение как прочитанное
    message.is_read = True
    db.commit()
    
    return {"status": "success"}
