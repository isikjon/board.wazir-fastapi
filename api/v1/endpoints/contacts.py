from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from jose import jwt

from app import models, schemas
from app.api import deps
from app.utils.security import ALGORITHM
from config import settings
from database import SessionLocal

router = APIRouter()

# Функция для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def get_users_for_chat(
    request: Request,
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> Any:
    """
    Получить список всех пользователей для чата, кроме текущего пользователя.
    """
    # Получаем токен из cookie или заголовка Authorization
    token = None
    cookies = request.cookies
    if "token" in cookies:
        token = cookies["token"]
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
    
    try:
        # Если есть токен, получаем текущего пользователя
        current_user_id = None
        if token:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            current_user_id = int(payload.get("sub"))
        
        # Получаем всех активных пользователей
        query = db.query(models.User).filter(models.User.is_active == True)
        
        # Если есть текущий пользователь, исключаем его из списка
        if current_user_id:
            query = query.filter(models.User.id != current_user_id)
        
        users = query.all()
        
        # Преобразуем в формат JSON
        result = []
        for user in users:
            result.append({
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email if user.email else ""
            })
        return result
    except Exception as e:
        # В случае ошибки логируем и все равно пытаемся получить всех пользователей
        print(f"Ошибка при получении пользователей: {str(e)}")
        try:
            # Пробуем получить всех пользователей без фильтров
            all_users = db.query(models.User).all()
            result = []
            for user in all_users:
                result.append({
                    "id": user.id,
                    "full_name": user.full_name,
                    "email": user.email if user.email else ""
                })
            return result
        except Exception as inner_e:
            print(f"Ошибка при вторичной попытке получения пользователей: {str(inner_e)}")
            return []
