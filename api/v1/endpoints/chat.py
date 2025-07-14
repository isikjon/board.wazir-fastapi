from typing import Any, List, Dict
from jose import jwt
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import datetime

from fastapi import APIRouter, Request, Depends, Body, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.models.chat_message import ChatMessage
from app.models.chat import AppChatModel
from app.models.user import User
from app.utils.security import ALGORITHM
from database import SessionLocal
from config import settings

router = APIRouter()

# Получение сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Получение текущего пользователя из токена
def get_current_user_from_token(token: str, db: Session) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        return user
    except Exception as e:
        return None


@router.get("/")
def get_chats(request: Request, db: Session = Depends(get_db)) -> Any:
    """
    Получить список чатов пользователя из БД.
    """
    # Получаем токен из cookie или заголовка
    token = None
    cookies = request.cookies
    if "token" in cookies:
        token = cookies["token"]
    else:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
    
    # Проверяем токен и получаем пользователя
    if not token:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    current_user = get_current_user_from_token(token, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Недействительный токен")
    
    # Получаем чаты пользователя из БД
    chats = db.query(AppChatModel).filter(
        or_(
            AppChatModel.user1_id == current_user.id,
            AppChatModel.user2_id == current_user.id
        )
    ).all()
    
    # Если чатов нет, возвращаем пустой список
    if not chats:
        return []
    
    # Формируем результат
    result = []
    for chat in chats:
        # Определяем собеседника
        other_user_id = chat.user2_id if chat.user1_id == current_user.id else chat.user1_id
        other_user = db.query(User).filter(User.id == other_user_id).first()
        
        # Получаем последнее сообщение
        last_message = db.query(ChatMessage).filter(
            ChatMessage.chat_id == chat.id
        ).order_by(ChatMessage.id.desc()).first()
        
        # Считаем непрочитанные сообщения с обновленным запросом
        # Важно: используем distinct() чтобы избежать дублирования из-за возможных JOIN
        unread_count = db.query(ChatMessage).filter(
            ChatMessage.chat_id == chat.id,
            ChatMessage.sender_id != current_user.id,
            ChatMessage.is_read == False
        ).distinct().count()
        
        # Выводим в лог для отладки
        print(f"DEBUG: Чат {chat.id}, пользователь {other_user.id}, непрочитанных сообщений: {unread_count}")
        
        if other_user:
            result.append({
                "id": chat.id,
                "user": {
                    "id": other_user.id,
                    "full_name": other_user.full_name,
                    "email": other_user.email
                },
                "last_message": last_message.content if last_message else "",
                "last_message_time": last_message.created_at if last_message else None,
                "unread_count": unread_count
            })
    
    return result


@router.get("/{user_id}")
def get_chat_messages(request: Request, user_id: int, db: Session = Depends(get_db)) -> Any:
    """
    Получить сообщения чата с конкретным пользователем из БД.
    """
    # Получаем токен из cookie или заголовка
    token = None
    cookies = request.cookies
    if "token" in cookies:
        token = cookies["token"]
    else:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
    
    # Проверяем токен и получаем пользователя
    if not token:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    current_user = get_current_user_from_token(token, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Недействительный токен")
    
    # Находим или создаем чат между пользователями
    chat = db.query(AppChatModel).filter(
        or_(
            and_(AppChatModel.user1_id == current_user.id, AppChatModel.user2_id == user_id),
            and_(AppChatModel.user1_id == user_id, AppChatModel.user2_id == current_user.id)
        )
    ).first()
    
    # Если чата нет, создаем новый
    if not chat:
        chat = AppChatModel(
            user1_id=current_user.id,
            user2_id=user_id
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return []  # Новый чат без сообщений
    
    # Получаем сообщения из БД
    messages = db.query(ChatMessage).filter(
        ChatMessage.chat_id == chat.id
    ).order_by(ChatMessage.created_at).all()
    
    # Отмечаем сообщения как прочитанные
    for msg in messages:
        if msg.sender_id != current_user.id and not msg.is_read:
            msg.is_read = True
    
    db.commit()
    
    # Формируем результат
    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "receiver_id": current_user.id if msg.sender_id != current_user.id else user_id,
            "content": msg.content,
            "sent_at": msg.created_at.isoformat()
        })
    
    return result


@router.post("/{user_id}")
def send_message(request: Request, user_id: int, content: str = Body(..., embed=True), db: Session = Depends(get_db)) -> Any:
    """
    Отправить сообщение пользователю и сохранить в БД.
    """
    # Получаем токен из cookie или заголовка
    token = None
    cookies = request.cookies
    if "token" in cookies:
        token = cookies["token"]
    else:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
    
    # Проверяем токен и получаем пользователя
    if not token:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    current_user = get_current_user_from_token(token, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    # Находим или создаем чат между пользователями
    chat = db.query(AppChatModel).filter(
        or_(
            and_(AppChatModel.user1_id == current_user.id, AppChatModel.user2_id == user_id),
            and_(AppChatModel.user1_id == user_id, AppChatModel.user2_id == current_user.id)
        )
    ).first()
    
    # Если чата нет, создаем новый
    if not chat:
        chat = AppChatModel(
            user1_id=current_user.id,
            user2_id=user_id
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
    
    # Создаем новое сообщение
    message = ChatMessage(
        chat_id=chat.id,
        sender_id=current_user.id,
        content=content,
        is_read=False
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return {
        "id": message.id,
        "sender_id": message.sender_id,
        "receiver_id": user_id,
        "content": message.content,
        "sent_at": message.created_at.isoformat()
    }


@router.post("/messages/read")
def mark_message_as_read(request: Request, message_id: int = Body(..., embed=True), db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Отметить сообщение как прочитанное.
    """
    # Получаем токен из cookie или заголовка
    token = None
    cookies = request.cookies
    if "token" in cookies:
        token = cookies["token"]
    else:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
    
    # Проверяем токен и получаем пользователя
    if not token:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    current_user = get_current_user_from_token(token, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Недействительный токен")
    
    # Находим сообщение по ID
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    
    # Если сообщение не найдено, возвращаем ошибку
    if not message:
        return {"success": False, "error": "Сообщение не найдено"}
    
    # Получаем ID отправителя сообщения
    sender_id = message.sender_id
    
    # Отмечаем как прочитанные ВСЕ сообщения от этого отправителя во всех возможных чатах
    # Это позволит обработать и чаты с ID в формате "1-2" и в формате "4"
    
    # Находим все чаты между текущим пользователем и отправителем
    chats = db.query(AppChatModel).filter(
        or_(
            and_(AppChatModel.user1_id == current_user.id, AppChatModel.user2_id == sender_id),
            and_(AppChatModel.user1_id == sender_id, AppChatModel.user2_id == current_user.id)
        )
    ).all()
    
    if not chats:
        return {"success": False, "error": "Чат не найден"}
    
    # Для каждого найденного чата отмечаем все сообщения от отправителя как прочитанные
    total_messages_updated = 0
    
    for chat in chats:
        print(f"DEBUG: Отмечаем сообщения как прочитанные в чате {chat.id} от пользователя {sender_id}")
        
        # Обновляем все непрочитанные сообщения от отправителя в этом чате
        updated = db.query(ChatMessage).filter(
            ChatMessage.chat_id == chat.id,
            ChatMessage.sender_id == sender_id,
            ChatMessage.is_read == False
        ).update({ChatMessage.is_read: True})
        
        total_messages_updated += updated
    
    # Фиксируем изменения в базе данных
    db.commit()
    
    return {
        "success": True, 
        "message": f"Отмечено как прочитанные {total_messages_updated} сообщений"
    }
