from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from jose import jwt

from app import models
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

# Получение текущего пользователя из токена
def get_current_user_from_token(token: str, db: Session) -> models.User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return None
        return user
    except Exception as e:
        print(f"DEBUG: Ошибка при декодировании токена: {e}")
        return None


@router.post("/{property_id}")
def add_to_favorites(
    property_id: int,
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Добавить объявление в избранное
    """
    # Получаем токен из cookie или заголовка
    token = None
    cookies = request.cookies
    if "access_token" in cookies:
        token = cookies["access_token"]
    else:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
    
    if not token:
        raise HTTPException(status_code=401, detail="Необходима авторизация")
    
    current_user = get_current_user_from_token(token, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Недействительный токен")
    
    # Проверяем существование объявления
    property_item = db.query(models.Property).filter(models.Property.id == property_id).first()
    if not property_item:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    
    # Проверяем, не добавлено ли уже в избранное
    existing_favorite = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id,
        models.Favorite.property_id == property_id
    ).first()
    
    if existing_favorite:
        return {"status": "already_exists", "message": "Объявление уже в избранном"}
    
    # Добавляем в избранное
    new_favorite = models.Favorite(
        user_id=current_user.id,
        property_id=property_id
    )
    
    db.add(new_favorite)
    db.commit()
    db.refresh(new_favorite)
    
    return {"status": "success", "message": "Объявление добавлено в избранное"}


@router.delete("/{property_id}")
def remove_from_favorites(
    property_id: int,
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Удалить объявление из избранного
    """
    # Получаем токен из cookie или заголовка
    token = None
    cookies = request.cookies
    if "access_token" in cookies:
        token = cookies["access_token"]
    else:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
    
    if not token:
        raise HTTPException(status_code=401, detail="Необходима авторизация")
    
    current_user = get_current_user_from_token(token, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Недействительный токен")
    
    # Находим запись в избранном
    favorite = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id,
        models.Favorite.property_id == property_id
    ).first()
    
    if not favorite:
        raise HTTPException(status_code=404, detail="Объявление не найдено в избранном")
    
    # Удаляем из избранного
    db.delete(favorite)
    db.commit()
    
    return {"status": "success", "message": "Объявление удалено из избранного"}


@router.get("/")
def get_favorites(
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Получить список избранных объявлений пользователя
    """
    # Получаем токен из cookie или заголовка
    token = None
    cookies = request.cookies
    if "access_token" in cookies:
        token = cookies["access_token"]
    else:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
    
    if not token:
        raise HTTPException(status_code=401, detail="Необходима авторизация")
    
    current_user = get_current_user_from_token(token, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Недействительный токен")
    
    # Получаем избранные объявления
    favorites = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id
    ).all()
    
    # Получаем полную информацию об объявлениях
    property_ids = [fav.property_id for fav in favorites]
    properties = db.query(models.Property).filter(
        models.Property.id.in_(property_ids)
    ).all()
    
    # Форматируем результат
    result = []
    for prop in properties:
        result.append({
            "id": prop.id,
            "title": prop.title,
            "description": prop.description,
            "price": prop.price,
            "address": prop.address,
            "city": prop.city,
            "area": prop.area,
            "status": prop.status,
            "type": prop.type,
            "rooms": prop.rooms
        })
    
    return result
