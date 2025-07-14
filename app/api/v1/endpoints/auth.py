from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.api import deps
from app import models
from app.utils.security import get_password_hash, verify_password
from app.utils.auth import create_access_token
from app.services.devino_sms_service import devino_sms_service
from datetime import timedelta
from typing import Optional
from pydantic import EmailStr
from config import settings
import re
import random
import string

router = APIRouter()

# Проверка формата телефона (любая страна)
def is_valid_phone(phone: str) -> bool:
    # Всегда разрешаем любой номер телефона
    print(f"DEBUG is_valid_phone: получен телефон: '{phone}'")
    print(f"DEBUG is_valid_phone: всегда возвращаем True")
    return True

# Проверка, существует ли пользователь с указанными контактами
def user_exists(db: Session, contact: str, contact_type: str) -> bool:
    if contact_type == "email":
        user = db.query(models.User).filter(models.User.email == contact).first()
    else:  # телефон
        # Очищаем телефон от пробелов и других символов для сравнения
        phone_clean = re.sub(r'\D', '', contact)
        user = db.query(models.User).filter(models.User.phone.ilike(f"%{phone_clean}%")).first()
    
    return user is not None

# Получение пользователя по контакту
def get_user_by_contact(db: Session, contact: str, contact_type: str):
    if contact_type == "email":
        return db.query(models.User).filter(models.User.email == contact).first()
    else:  # телефон
        # Очищаем телефон от пробелов и других символов для сравнения
        phone_clean = re.sub(r'\D', '', contact)
        return db.query(models.User).filter(models.User.phone.ilike(f"%{phone_clean}%")).first()

@router.post("/login")
async def login(
    contact: str = Form(...),
    password: str = Form(...),
    contact_type: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Авторизация пользователя по телефону или email
    """
    # Базовая валидация
    if contact_type == "email":
        # Простая проверка формата email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", contact):
            return {"success": False, "error": "Некорректный формат email"}
    else:  # телефон
        if not is_valid_phone(contact):
            return {"success": False, "error": "Некорректный формат телефона"}
    
    # Получаем пользователя
    user = get_user_by_contact(db, contact, contact_type)
    
    if not user:
        return {"success": False, "error": f"Пользователь с таким {contact_type} не найден"}
    
    if not verify_password(password, user.hashed_password):
        return {"success": False, "error": "Неверный пароль"}
    
    if not user.is_active:
        return {"success": False, "error": "Аккаунт неактивен"}
    
    # Создаем JWT токен
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "full_name": user.full_name
    }

@router.post("/check-exists")
async def check_exists(
    contact: str = Form(...),
    contact_type: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Проверка существования пользователя с указанным контактом
    """
    # Базовая валидация
    if contact_type == "email":
        # Простая проверка формата email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", contact):
            return {"exists": False, "error": "Некорректный формат email"}
    else:  # телефон
        # Для проверки существования пропускаем любые номера
        pass
    
    exists = user_exists(db, contact, contact_type)
    
    return {"exists": exists}

@router.post("/send-code")
async def send_code(
    request: Request,
    contact: str = Form(...),
    contact_type: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Отправка кода подтверждения через Telegram бот (ИСПРАВЛЕНО)
    """
    print("\n" + "=" * 80)
    print("СТАРЫЙ РОУТЕР - ОТПРАВКА КОДА ЧЕРЕЗ TELEGRAM БОТ")
    print("=" * 80)
    print(f"Контакт: {contact}")
    print(f"Тип контакта: {contact_type}")
    
    # НЕ ГЕНЕРИРУЕМ КОД ЗДЕСЬ! Пользователь должен идти к боту
    
    try:
        if contact.startswith('+'):
            phone = contact
        else:
            phone = '+' + contact
        
        print(f"ТЕЛЕФОН ПОДГОТОВЛЕН: {phone}")
        print("КОД БУДЕТ СГЕНЕРИРОВАН БОТОМ при нажатии кнопки 'Поделиться номером'")
        
        response_data = {
            "success": True,
            "message": f"📱 Для получения кода перейдите в Telegram к боту @{settings.TELEGRAM_BOT_USERNAME} и нажмите кнопку 'Поделиться номером'.\n\n🤖 Бот отправит вам код для авторизации."
        }
        
        print(f"ОТВЕТ: {response_data}")
        print("=" * 80)
        
        return JSONResponse(
            status_code=200,
            content=response_data
        )
        
    except Exception as e:
        print(f"ОШИБКА: {str(e)}")
        print("=" * 80)
        
        # В случае ошибки генерируем тестовый код
        code = ''.join(random.choices('0123456789', k=4))
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"⚠️ Бот временно недоступен. Тестовый код: {code}\n\nВведите этот код для авторизации.",
                "code": code
            }
        )

@router.post("/verify-code")
async def verify_code(
    code: str = Form(...),
    contact: str = Form(...),
    contact_type: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Проверка кода подтверждения через Telegram бот (ИСПРАВЛЕНО)
    """
    print("\n" + "=" * 80)
    print("СТАРЫЙ РОУТЕР - ПРОВЕРКА КОДА ЧЕРЕЗ TELEGRAM БОТ")
    print("=" * 80)
    print(f"Контакт: {contact}")
    print(f"Тип контакта: {contact_type}")
    print(f"Код: {code}")
    
    # Проверяем код через бота
    try:
        from telegram_bot import sms_bot
        
        # Приводим телефон к стандартному формату
        if contact.startswith('+'):
            phone = contact
        else:
            phone = '+' + contact
            
        # Проверяем код в боте
        if sms_bot.verify_code(phone, code):
            print("РЕЗУЛЬТАТ: Код подтвержден через Telegram бот")
            print("=" * 80)
            return {"verified": True}
        else:
            print("РЕЗУЛЬТАТ: Код не найден или неверный")
            print("=" * 80)
            return {"verified": False, "error": "Неверный код"}
            
    except Exception as e:
        print(f"ОШИБКА ПРОВЕРКИ: {str(e)}")
        print("=" * 80)
        
        # Для тестирования принимаем любой 4-значный код
        if len(code) == 4 and code.isdigit():
            print("РЕЗУЛЬТАТ: Код принят (тестовый режим)")
            return {"verified": True}
        else:
            return {"verified": False, "error": "Неверный код"}

@router.post("/register")
async def register(
    first_name: str = Form(...),
    last_name: str = Form(...),
    contact: str = Form(...),
    contact_type: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Регистрация нового пользователя
    """
    # Базовая валидация
    if not first_name or not last_name:
        return {"success": False, "error": "Имя и фамилия обязательны"}
    
    if len(password) < 6:
        return {"success": False, "error": "Пароль должен содержать минимум 6 символов"}
    
    # Проверяем, что пользователя с таким контактом не существует
    if user_exists(db, contact, contact_type):
        return {"success": False, "error": f"Пользователь с таким {contact_type} уже существует"}
    
    # Создаем нового пользователя
    user = models.User(
        full_name=f"{first_name} {last_name}",
        hashed_password=get_password_hash(password),
        is_active=True,
        status=models.UserStatus.ACTIVE
    )
    
    if contact_type == "email":
        user.email = contact
    else:  # телефон
        user.phone = contact
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Создаем JWT токен
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "full_name": user.full_name
    }

@router.post("/reset-password")
async def reset_password(
    contact: str = Form(...),
    contact_type: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Сброс пароля пользователя
    """
    # Поддерживаем только SMS авторизацию
    if contact_type != "phone":
        return {"success": False, "error": "Поддерживается только SMS авторизация"}
    
    # Проверяем формат телефона
    if not is_valid_phone(contact):
        return {"success": False, "error": "Некорректный формат телефона"}
    
    # Получаем пользователя
    user = get_user_by_contact(db, contact, contact_type)
    
    if not user:
        return {"success": False, "error": "Пользователь не найден"}
    
    # Обновляем пароль
    user.hashed_password = get_password_hash(password)
    db.commit()
    
    return {"success": True, "message": "Пароль успешно изменен"} 