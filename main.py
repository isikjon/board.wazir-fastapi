import os
import uuid
import json
import sys
import asyncio
import subprocess
import openpyxl
import pandas as pd
import random
import shutil
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from io import BytesIO
from uuid import uuid4
from pathlib import Path
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, Form, status, HTTPException, Query, WebSocket, WebSocketDisconnect, Response, UploadFile, File, APIRouter
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_, and_, asc, text
from sqlalchemy.types import String

from passlib.context import CryptContext
from jose import JWTError, jwt
from jose import jwt as pyjwt

from config import settings
from api.v1.api import api_router
from app.api import deps
from app.utils.security import verify_password
from app import models
from app.models.user import User
from app.models.token import TokenPayload
from app.models.chat import AppChatModel, AppChatMessageModel
from app.models.chat_message import ChatMessage
from app.models.property import PropertyImage
from app.websockets.chat_manager import ConnectionManager as WebSocketManager
from app.utils.image_helper import get_valid_image_url
from app.models.property import PropertyCategory
from app.models.service import ServiceCategory, ServiceCard, ServiceCardImage

try:
    from app.services.telegram_bot_service import telegram_bot_service
    telegram_bot_available = True
except ImportError as e:
    print(f"Telegram бот недоступен: {e}")
    telegram_bot_service = None
    telegram_bot_available = False

try:
    import psutil
except ImportError:
    psutil = None

try:
    from flask import jsonify
except ImportError:
    pass

# Импортируем простой бот с nest_asyncio
try:
    from telegram_bot import sms_bot
    simple_bot_available = True
except ImportError:
    simple_bot_available = False
    sms_bot = None

# Функция для загрузки категорий из JSON файла
def load_categories_from_json():
    """Загрузка категорий из JSON файла"""
    try:
        with open('categories.json', 'r', encoding='utf-8') as f:
            categories = json.load(f)
        
        print(f"=== ЗАГРУЗКА КАТЕГОРИЙ ===")
        print(f"Всего категорий загружено: {len(categories)}")
        
        # Подсчитываем по уровням
        level_1 = [c for c in categories if c.get('level', 1) == 1]
        level_2 = [c for c in categories if c.get('level', 1) == 2]
        level_3 = [c for c in categories if c.get('level', 1) == 3]
        
        print(f"Уровень 1: {len(level_1)} категорий")
        print(f"Уровень 2: {len(level_2)} категорий")  
        print(f"Уровень 3: {len(level_3)} категорий")
        
        # Выводим подробную информацию о категории "Для дома и дачи"
        home_garden = [c for c in categories if c.get('name') == 'Для дома и дачи']
        if home_garden:
            cat = home_garden[0]
            print(f"=== КАТЕГОРИЯ 'ДЛЯ ДОМА И ДАЧИ' ===")
            print(f"ID: {cat.get('id')}")
            print(f"Название: {cat.get('name')}")
            print(f"Уровень: {cat.get('level')}")
            print(f"Есть дети: {cat.get('has_children')}")
            print(f"Тип has_children: {type(cat.get('has_children'))}")
        
        # Выводим подкатегории для категории 6
        subcategories = [c for c in categories if c.get('parent_id') == 6]
        print(f"=== ПОДКАТЕГОРИИ ДЛЯ КАТЕГОРИИ 6 ===")
        print(f"Найдено подкатегорий: {len(subcategories)}")
        for sub in subcategories:
            print(f"  - ID: {sub.get('id')}, Название: {sub.get('name')}, Parent ID: {sub.get('parent_id')}")
        
        # Выводим бренды для подкатегории 61
        brands = [c for c in categories if c.get('parent_id') == 61]
        print(f"=== БРЕНДЫ ДЛЯ ПОДКАТЕГОРИИ 61 ===")
        print(f"Найдено брендов: {len(brands)}")
        for brand in brands:
            print(f"  - ID: {brand.get('id')}, Название: {brand.get('name')}, Parent ID: {brand.get('parent_id')}")
        
        print(f"=== ЗАГРУЗКА КАТЕГОРИЙ ЗАВЕРШЕНА ===")
        return categories
        
    except FileNotFoundError:
        print("DEBUG: Файл categories.json не найден, используем категории по умолчанию")
        return [
            {"id": 1, "name": "Недвижимость", "slug": "real-estate", "image": "https://wazir.kg/board/categories/1.png", "parent_id": None, "level": 1, "has_children": False},
            {"id": 2, "name": "Авто", "slug": "auto", "image": "https://wazir.kg/board/categories/2.png", "parent_id": None, "level": 1, "has_children": False},
            {"id": 3, "name": "Работа", "slug": "jobs", "image": "https://wazir.kg/board/categories/3.png", "parent_id": None, "level": 1, "has_children": False},
            {"id": 4, "name": "Услуги", "slug": "services", "image": "https://wazir.kg/board/categories/4.png", "parent_id": None, "level": 1, "has_children": False},
            {"id": 5, "name": "Бытовая техника", "slug": "appliances", "image": "https://wazir.kg/board/categories/5.png", "parent_id": None, "level": 1, "has_children": False},
        ]
    except Exception as e:
        print(f"DEBUG: Ошибка загрузки categories.json: {e}")
        return []

def get_categories_by_parent(parent_id=None):
    """Получить категории по parent_id"""
    all_categories = load_categories_from_json()
    return [cat for cat in all_categories if cat.get('parent_id') == parent_id]

def get_category_by_id(category_id):
    """Получить категорию по ID"""
    all_categories = load_categories_from_json()
    for cat in all_categories:
        if cat.get('id') == category_id:
            return cat
    return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ОТКЛЮЧАЕМ сложный бот с системой сессий
    # if telegram_bot_available and telegram_bot_service:
    #     print("Запуск Telegram бота...")
    #     await telegram_bot_service.start_bot()
    # else:
    #     print("Telegram бот не запущен (не настроен или недоступен)")
    
    # 🔥 ПРИНУДИТЕЛЬНЫЙ ЗАПУСК ПРОСТОГО БОТА 🔥
    print("🚀 Принудительный запуск простого Telegram бота...")
    try:
        # Проверяем настройки
        if not settings.TELEGRAM_BOT_TOKEN:
            print("❌ TELEGRAM_BOT_TOKEN не настроен!")
        elif not settings.TELEGRAM_BOT_USERNAME:
            print("❌ TELEGRAM_BOT_USERNAME не настроен!")
        else:
            print(f"✅ Настройки найдены: @{settings.TELEGRAM_BOT_USERNAME}")
            
            # Импортируем бота принудительно
            try:
                from telegram_bot import sms_bot
                print("✅ telegram_bot импортирован успешно")
                
                # Запускаем бота в отдельной задаче БЕЗ ОЖИДАНИЯ
                asyncio.create_task(sms_bot.start_bot())
                print("✅ Задача запуска бота создана")
                
                # Даем боту время запуститься
                await asyncio.sleep(1)
                
            except ImportError as e:
                print(f"❌ Ошибка импорта telegram_bot: {e}")
            except Exception as e:
                print(f"❌ Ошибка запуска бота: {e}")
                import traceback
                print(f"❌ Traceback: {traceback.format_exc()}")
    except Exception as e:
        print(f"❌ Критическая ошибка при запуске бота: {e}")
    
    print("🚀 Приложение запущено")
    yield
    
    # Останавливаем простой бот
    print("🛑 Остановка простого Telegram бота...")
    try:
        from telegram_bot import sms_bot
        await sms_bot.stop_bot()
    except Exception as e:
        print(f"❌ Ошибка остановки простого бота: {e}")
    
    print("🛑 Приложение завершено")

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = pyjwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# Класс для аутентификации HTTP запросов (но не WebSocket)
class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Проверяем, является ли запрос WebSocket
        if request.scope.get("type") == "websocket":
            # Для WebSocket запросов пропускаем проверку
            return await call_next(request)
        
        # Пути, доступные без авторизации
        public_paths = [
            '/mobile/auth',
            '/mobile/register',
            '/mobile/register/verify',
            '/mobile/register/profile',
            '/mobile/reset',
            '/mobile/reset/verify',
            '/mobile/reset/password',
            '/api/v1/auth/login',
            '/api/v1/auth/check-exists',
            '/api/v1/auth/send-code',
            '/api/v1/auth/verify-code',
            '/api/v1/auth/register',
            '/api/v1/auth/reset-password',
            '/api/v1/telegram/initiate',
            '/api/v1/telegram/verify-phone',
            '/api/v1/telegram/verify-code',
            '/api/v1/telegram/status',
            '/api/v1/telegram/force-reset',
            '/favicon.ico',
            '/mobile/test-websocket',
            '/mobile/ws/',
            '/api/v1/chat/',  # Chat API general path
            '/admin/login',   # Admin login page
            '/superadmin/login',  # SuperAdmin login page
            '/companies/login',   # Company login page
        ]
        
        # Для статических файлов разрешаем доступ
        if request.url.path.startswith('/static/'):
            return await call_next(request)
            
        # Для API запросов - НЕ ПРОВЕРЯЕМ ТОКЕН В MIDDLEWARE
        # Пусть каждый API эндпоинт сам проверяет токен через deps.get_current_active_user
        if request.url.path.startswith('/api/'):
            # Разрешаем доступ к эндпоинтам авторизации без токена
            if any(request.url.path.endswith(path) for path in [
                '/login',
                '/register',
                '/check-exists',
                '/send-code',
                '/verify-code',
                '/reset-password'
            ]):
                return await call_next(request)
                
            # ДЛЯ ВСЕХ ОСТАЛЬНЫХ API ЭНДПОИНТОВ - ПРОСТО ПРОПУСКАЕМ
            # Аутентификация будет происходить через deps.get_current_active_user
            return await call_next(request)
            
        if any(request.url.path.startswith(path) for path in public_paths) or '/api/v1/chat/' in request.url.path:
            return await call_next(request)
            
        auth_token = request.cookies.get('access_token')
        auth_header = request.headers.get('Authorization')
        
        print(f"DEBUG: Checking auth for path: {request.url.path}")
        print(f"DEBUG: Cookie token: {auth_token}")
        print(f"DEBUG: Auth header: {auth_header}")
        
        if auth_header and auth_header.startswith('Bearer '):
            auth_token = auth_header.split(' ')[1]
            print(f"DEBUG: Using token from header: {auth_token}")
        
        if not auth_token:
            print("DEBUG: No token found")
            if request.url.path.startswith('/admin/'):
                return RedirectResponse('/admin/login', status_code=303)
            elif request.url.path.startswith('/superadmin/'):
                return RedirectResponse('/superadmin/login', status_code=303)
            elif request.url.path.startswith('/companies/'):
                return RedirectResponse('/companies/login', status_code=303)
            # Для остальных маршрутов перенаправляем на страницу авторизации
            return RedirectResponse('/mobile/auth', status_code=303)
            
        # Проверяем валидность токена
        try:
            payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            print(f"DEBUG: Token payload: {payload}")
            if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
                print("DEBUG: Token expired")
                if request.url.path.startswith('/admin/'):
                    return RedirectResponse('/admin/login', status_code=303)
                elif request.url.path.startswith('/superadmin/'):
                    return RedirectResponse('/superadmin/login', status_code=303)
                elif request.url.path.startswith('/companies/'):
                    return RedirectResponse('/companies/login', status_code=303)
                return RedirectResponse('/mobile/auth', status_code=303)
                
            # Для суперадмин-маршрутов проверяем, что пользователь является суперадминистратором
            if request.url.path.startswith('/superadmin/') and not payload.get("is_superadmin"):
                print("DEBUG: Non-superadmin user trying to access superadmin area")
                return RedirectResponse('/superadmin/login', status_code=303)
                
            # Для админ-маршрутов проверяем, что пользователь является администратором
            if request.url.path.startswith('/admin/') and not payload.get("is_admin"):
                print("DEBUG: Non-admin user trying to access admin area")
                return RedirectResponse('/admin/login', status_code=303)
                
            # Для маршрутов компаний проверяем, что пользователь является компанией
            if request.url.path.startswith('/companies/') and not payload.get("is_company"):
                print("DEBUG: Non-company user trying to access company area")
                return RedirectResponse('/companies/login', status_code=303)
                
        except Exception as e:
            print(f"DEBUG: Token validation error (cookie): {str(e)}")
            if request.url.path.startswith('/admin/'):
                return RedirectResponse('/admin/login', status_code=303)
            elif request.url.path.startswith('/superadmin/'):
                return RedirectResponse('/superadmin/login', status_code=303)
            elif request.url.path.startswith('/companies/'):
                return RedirectResponse('/companies/login', status_code=303)
            return RedirectResponse('/mobile/auth', status_code=303)
            
        # Если токен валиден, пропускаем запрос дальше
        return await call_next(request)

# Кастомный JSON-энкодер для обработки datetime и других неподдерживаемых типов
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        return super().default(obj)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "Set-Cookie"],
)

app.add_middleware(SessionMiddleware, secret_key="wazir_super_secret_key")

# Функция для сериализации объектов в JSON, используя CustomJSONEncoder
def json_serialize(obj):
    return json.dumps(obj, cls=CustomJSONEncoder)

@app.exception_handler(TypeError)
async def type_error_handler(request, exc):
    if "not JSON serializable" in str(exc):
        return JSONResponse(
            status_code=500,
            content={"detail": "Error serializing the response"},
        )
    raise exc

templates = Jinja2Templates(directory="templates")

# Регистрация API роутеров
app.include_router(api_router, prefix=settings.API_V1_STR)

# Добавляем мидлвар для проверки авторизации
app.add_middleware(AuthenticationMiddleware)

# WebSocket Manager class
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.chat_messages: Dict[str, List[dict]] = {}
        # Загружаем сохраненные сообщения, если файл существует
        try:
            if os.path.exists("chat_messages.json"):
                with open("chat_messages.json", "r", encoding="utf-8") as f:
                    data = f.read()
                    if data.strip():  # проверяем, что файл не пустой
                        self.chat_messages = json.loads(data)
                        print(f"DEBUG: Загружены сохраненные сообщения чатов. Доступные комнаты: {list(self.chat_messages.keys())}")
                        for room, messages in self.chat_messages.items():
                            print(f"DEBUG: Комната {room}: {len(messages)} сообщений")
                            # Выводим первое и последнее сообщение для отладки
                            if messages:
                                print(f"DEBUG: Первое сообщение: {messages[0].get('content', 'Нет контента')}")
                                print(f"DEBUG: Последнее сообщение: {messages[-1].get('content', 'Нет контента')}")
                    else:
                        print("DEBUG: Файл с сообщениями пуст, создаем новый")
                        with open("chat_messages.json", "w", encoding="utf-8") as f:
                            json.dump({}, f, ensure_ascii=False, indent=2)
            else:
                print("DEBUG: Файл с сообщениями не найден, создаем новый")
                with open("chat_messages.json", "w", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"DEBUG: Ошибка при загрузке сообщений: {e}")
            # Создаем пустой файл в случае ошибки
            try:
                with open("chat_messages.json", "w", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
            except Exception as e2:
                print(f"DEBUG: Не удалось создать пустой файл: {e2}")

    async def connect(self, websocket: WebSocket, room: str, accept_connection: bool = True):
        if accept_connection:
            await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        if websocket not in self.active_connections[room]:
            self.active_connections[room].append(websocket)
            print(f"DEBUG: Подключен к комнате {room}, всего подключений: {len(self.active_connections[room])}")
        else:
            print(f"DEBUG: Соединение уже подключено к комнате {room}")

    def disconnect(self, websocket: WebSocket, room: str):
        try:
            if room in self.active_connections:
                if websocket in self.active_connections[room]:
                    self.active_connections[room].remove(websocket)
                    print(f"DEBUG: Отключен от комнаты {room}, осталось подключений: {len(self.active_connections[room])}")
                if not self.active_connections[room]:
                    del self.active_connections[room]
                    print(f"DEBUG: Комната {room} удалена, нет активных подключений")
        except Exception as e:
            print(f"DEBUG: Ошибка при отключении от комнаты {room}: {e}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    # Метод для сохранения сообщений в файл
    def save_messages_to_file(self):
        try:
            with open("chat_messages.json", "w", encoding="utf-8") as f:
                json.dump(self.chat_messages, f, ensure_ascii=False, indent=2)
            print(f"DEBUG: Сообщения сохранены в файл. Всего комнат: {len(self.chat_messages)}")
        except Exception as e:
            print(f"ERROR: Ошибка при сохранении сообщений в файл: {e}")
    
    # Метод для добавления сообщения в память и сохранения в файл
    def add_message_to_memory(self, chat_id: str, message: dict):
        if chat_id not in self.chat_messages:
            self.chat_messages[chat_id] = []
        
        # Добавляем сообщение в память
        self.chat_messages[chat_id].append(message)
        
        # Сохраняем в файл после добавления нового сообщения
        self.save_messages_to_file()
    
    async def broadcast(self, message: dict, room: str, exclude=None):
        # Если это сообщение чата, сохраняем его в памяти
        if message.get("type") in ["message", "message_sent", "new_message"] and "message" in message:
            chat_id = str(message["message"].get("chat_id", room))
            self.add_message_to_memory(chat_id, message["message"])
        
        # Отправляем сообщение всем активным соединениям в комнате
        if room in self.active_connections:
            for connection in self.active_connections[room]:
                if connection != exclude:
                    await connection.send_json(message)

    def save_message(self, room: str, message: dict):
        if room not in self.chat_messages:
            self.chat_messages[room] = []
        self.chat_messages[room].append(message)
        # Сохраняем сообщения в файл для персистентности
        try:
            # Преобразуем datetime в строку для сериализации
            serializable_messages = {}
            for room_key, messages in self.chat_messages.items():
                serializable_messages[room_key] = []
                for msg in messages:
                    # Копируем сообщение и обрабатываем timestamp, если нужно
                    if isinstance(msg, dict):
                        serializable_messages[room_key].append(msg)
                    else:
                        # Если сообщение не словарь, преобразуем его в строку
                        serializable_messages[room_key].append(str(msg))
            
            with open("chat_messages.json", "w", encoding="utf-8") as f:
                json.dump(serializable_messages, f, ensure_ascii=False, indent=2)
                
            print(f"DEBUG: Сохранено сообщение в комнату {room}, всего сообщений: {len(self.chat_messages[room])}")
        except Exception as e:
            print(f"DEBUG: Ошибка при сохранении сообщений: {e}")

    def get_messages(self, room: str) -> List[dict]:
        """Получить все сообщения для указанной комнаты"""
        return self.chat_messages.get(room, [])
        
    async def save_message_to_db(self, message_data: dict, db: Session) -> dict:
        """Сохраняет сообщение в базу данных и возвращает его с дополнительными полями"""
        try:
            # Создаем полную копию данных сообщения
            saved_message = message_data.copy()
            
            # Добавляем timestamp если его нет
            current_time = datetime.now()
            saved_message["timestamp"] = current_time.isoformat()
            saved_message["is_read"] = False
            # Используем целочисленный ID вместо UUID для совместимости с предложенной структурой БД
            saved_message["id"] = random.randint(100, 10000)
            
            # Определяем комнату для сообщения (всегда используем меньший ID первым)
            sender_id = int(saved_message["sender_id"])
            receiver_id = int(saved_message["receiver_id"])
            room = f"{min(sender_id, receiver_id)}_{max(sender_id, receiver_id)}"
            
            # Сохраняем сообщение
            self.save_message(room, saved_message)
            
            print(f"DEBUG: Сообщение сохранено: {saved_message}")
            return saved_message
        except Exception as e:
            print(f"ERROR: Ошибка при сохранении сообщения: {e}")
            # Возвращаем базовое сообщение с временной меткой в случае ошибки
            basic_message = message_data.copy()
            basic_message["timestamp"] = datetime.now().isoformat()
            basic_message["is_read"] = False
            basic_message["id"] = str(uuid4())
            return basic_message

manager = ConnectionManager()

# ============================ WebSocket Endpoints ============================
from sqlalchemy.orm import Session
from app.api import deps
from app.websockets.chat_manager import manager as chat_manager
from jose import jwt as pyjwt

@app.websocket("/mobile/ws/chat/{token}")
async def chat_websocket_endpoint(websocket: WebSocket, token: str):
    try:
        payload = pyjwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008)
            return
    except Exception as e:
        print(f"WebSocket auth error: {e}")
        await websocket.close(code=1008)
        return
        
    await chat_manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "message":
                db = next(deps.get_db())
                message_data = {
                    "sender_id": int(user_id),
                    "receiver_id": data["receiver_id"],
                    "content": data["content"]
                }
                
                saved_message = await chat_manager.save_message_to_db(message_data, db)
                
                await websocket.send_json({
                    "type": "message_sent",
                    "message": saved_message
                })
                
                # Добавляем получателя в данные для отправки
                broadcast_message = {
                    "type": "new_message",
                    "message": saved_message,
                    "receiver_id": data["receiver_id"]
                }
                await chat_manager.broadcast(broadcast_message)
    except WebSocketDisconnect:
        chat_manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        chat_manager.disconnect(websocket, user_id)

@app.websocket("/mobile/ws/test")
async def websocket_test_endpoint(websocket: WebSocket):
    print("WebSocket test connection request")
    await websocket.accept()
    print("WebSocket test connection accepted")
    
    try:
        while True:
            # Отправляем тестовое сообщение каждые 5 секунд
            test_message = {
                "type": "test",
                "message": f"Test message at {datetime.now().strftime('%H:%M:%S')}",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_text(json.dumps(test_message))
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        print("WebSocket test connection disconnected")

@app.websocket("/superadmin/ws/logs")
async def logs_websocket_endpoint(websocket: WebSocket):
    import subprocess
    import asyncio
    from datetime import datetime
    
    await websocket.accept()
    print("SuperAdmin logs WebSocket connection established")
    
    try:
        # Запускаем процесс для получения логов Docker
        process = subprocess.Popen(
            ["docker", "logs", "-f", "--tail", "50", "state.wazir-fastapi-web-1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        while True:
            # Читаем строку из логов
            line = process.stdout.readline()
            if line:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "message": line.strip(),
                    "level": "INFO"  # Можно добавить определение уровня лога
                }
                await websocket.send_text(json.dumps(log_entry))
            else:
                await asyncio.sleep(0.1)
                
    except WebSocketDisconnect:
        print("SuperAdmin logs WebSocket connection disconnected")
        if 'process' in locals():
            process.terminate()
    except Exception as e:
        print(f"Error in logs WebSocket: {e}")
        if 'process' in locals():
            process.terminate()

# Корневой маршрут - перенаправление на мобильную версию
@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(url="/mobile")

# Добавляем маршруты для доступа через /layout
@app.get("/layout", response_class=RedirectResponse)
async def layout_root():
    return RedirectResponse(url="/mobile")

@app.get("/layout/dashboard", response_class=RedirectResponse)
async def layout_dashboard():
    return RedirectResponse(url="/mobile")

@app.get("/layout/auth", response_class=RedirectResponse)
async def layout_auth():
    return RedirectResponse(url="/mobile/auth")

@app.get("/layout/profile", response_class=RedirectResponse)
async def layout_profile():
    return RedirectResponse(url="/mobile/profile")

@app.get("/layout/create-listing", response_class=RedirectResponse)
async def layout_create_listing():
    return RedirectResponse(url="/mobile/create-listing")

@app.get("/layout/search", response_class=RedirectResponse)
async def layout_search():
    return RedirectResponse(url="/mobile/search")

@app.get("/layout/property/{property_id}", response_class=RedirectResponse)
async def layout_property_detail(property_id: int):
    return RedirectResponse(url=f"/mobile/property/{property_id}")

# Новые страницы для аутентификации
@app.get("/register", response_class=RedirectResponse)
async def redirect_register():
    return RedirectResponse(url="/mobile/register")

@app.get("/reset", response_class=RedirectResponse)
async def redirect_reset():
    return RedirectResponse(url="/mobile/reset")

@app.get("/mobile/register", response_class=HTMLResponse, name="mobile_register")
async def mobile_register(request: Request):
    return templates.TemplateResponse("layout/register.html", {"request": request})

@app.get("/mobile/register/verify", response_class=HTMLResponse, name="mobile_register_verify")
async def mobile_register_verify(request: Request, db: Session = Depends(deps.get_db)):
    """
    Генерация кода подтверждения сразу при загрузке страницы
    """
    # Получаем контактные данные из query параметров или sessionStorage (будет получен на фронте)
    phone = request.query_params.get('phone')
    
    # Генерируем 4-значный код
    import random
    code = ''.join(random.choices('0123456789', k=4))
    
    # Если телефон передан, сохраняем код в БД
    if phone:
        try:
            # Приводим телефон к стандартному формату
            if not phone.startswith('+'):
                phone = '+' + phone
            
            # Проверяем, есть ли уже активный код для этого телефона
            existing_code = None
            try:
                from api.v1.endpoints.telegram_auth import load_verification_codes, save_verification_codes
                codes = load_verification_codes()
                
                if phone in codes:
                    stored_data = codes[phone]
                    time_diff = datetime.now() - stored_data['timestamp']
                    if time_diff <= timedelta(minutes=2):
                        existing_code = stored_data['code']
                        print(f"🔄 Используем существующий код {existing_code} для {phone}")
                
                # Генерируем новый код только если нет активного
                if not existing_code:
                    codes[phone] = {
                        'code': code,
                        'timestamp': datetime.now(),
                        'user_id': None
                    }
                    save_verification_codes(codes)
                    print(f"✅ Сгенерирован новый код {code} для {phone}")
                else:
                    code = existing_code
                    
            except Exception as e:
                print(f"❌ Ошибка работы с кодами: {e}")
                # Сохраняем код в память как fallback
                if not hasattr(mobile_register_verify, '_codes'):
                    mobile_register_verify._codes = {}
                mobile_register_verify._codes[phone] = {
                    'code': code,
                    'timestamp': datetime.now()
                }
                
        except Exception as e:
            print(f"❌ Ошибка генерации кода: {e}")
    
    # Возвращаем HTML с информацией о сгенерированном коде
    return templates.TemplateResponse("layout/verify.html", {
        "request": request,
        "generated_code": code,
        "phone": phone
    })

@app.get("/mobile/register/profile", response_class=HTMLResponse, name="mobile_profile_create")
async def mobile_profile_create(request: Request):
    return templates.TemplateResponse("layout/profile_create.html", {"request": request})

@app.get("/mobile/reset", response_class=HTMLResponse, name="mobile_reset")
async def mobile_reset(request: Request):
    return templates.TemplateResponse("layout/reset.html", {"request": request})

@app.get("/mobile/reset/verify", response_class=HTMLResponse, name="mobile_reset_verify")
async def mobile_reset_verify(request: Request):
    return templates.TemplateResponse("layout/reset_verify.html", {"request": request})

@app.get("/mobile/reset/password", response_class=HTMLResponse, name="mobile_reset_password")
async def mobile_reset_password(request: Request):
    return templates.TemplateResponse("layout/reset_password.html", {"request": request})

# Мобильные (клиентские) маршруты
@app.get("/mobile", response_class=HTMLResponse, name="dashboard")
async def mobile_root(request: Request):
    return templates.TemplateResponse("layout/dashboard.html", {"request": request})

@app.get("/mobile/auth", response_class=HTMLResponse, name="mobile_auth")
async def mobile_auth(request: Request):
    return templates.TemplateResponse("layout/auth.html", {"request": request})

@app.get("/mobile/services", response_class=HTMLResponse, name="services")
async def mobile_services(request: Request, db: Session = Depends(deps.get_db)):
    # Получаем все активные категории сервисов из БД
    categories = db.query(ServiceCategory).filter(ServiceCategory.is_active == True).all()
    
    return templates.TemplateResponse("layout/services.html", {
        "request": request,
        "categories": categories
    })

@app.get("/mobile/services/{category_slug}", response_class=HTMLResponse, name="service_category")
async def mobile_service_category(request: Request, category_slug: str, db: Session = Depends(deps.get_db)):
    # Получаем категорию по слагу
    category = db.query(ServiceCategory).filter(
        ServiceCategory.slug == category_slug,
        ServiceCategory.is_active == True
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    
    # Получаем все активные карточки заведений в данной категории С ИЗОБРАЖЕНИЯМИ
    service_cards = db.query(ServiceCard).options(
        joinedload(ServiceCard.images)
    ).filter(
        ServiceCard.category_id == category.id,
        ServiceCard.is_active == True
    ).all()
    
    return templates.TemplateResponse("layout/service_category.html", {
        "request": request,
        "category": category,
        "service_cards": service_cards
    })

@app.get("/mobile/services/card/{card_id}", response_class=HTMLResponse, name="service_detail")
async def mobile_service_detail(request: Request, card_id: int, db: Session = Depends(deps.get_db)):
    # Получаем карточку заведения по ID с изображениями
    service_card = db.query(ServiceCard).options(joinedload(ServiceCard.images)).filter(
        ServiceCard.id == card_id,
        ServiceCard.is_active == True
    ).first()
    
    if not service_card:
        raise HTTPException(status_code=404, detail="Заведение не найдено")
    
    # Получаем категорию
    category = db.query(ServiceCategory).filter(
        ServiceCategory.id == service_card.category_id
    ).first()
    
    # Получаем похожие заведения в той же категории (исключая текущее)
    similar_services = db.query(ServiceCard).filter(
        ServiceCard.category_id == service_card.category_id,
        ServiceCard.id != service_card.id,
        ServiceCard.is_active == True
    ).limit(6).all()
    
    # Добавляем has_360_tour к service_card
    service_card.has_360_tour = service_card.has_360_tour()
    
    return templates.TemplateResponse("layout/service_detail.html", {
        "request": request,
        "service_card": service_card,
        "category": category,
        "similar_services": similar_services
    })

@app.get("/mobile/profile", response_class=HTMLResponse, name="profile")
async def mobile_profile(request: Request, tab: str = None, db: Session = Depends(deps.get_db)):
    # Получаем текущего пользователя
    user = None
    formatted_user_listings = []
    formatted_saved_listings = []
    
    # Получаем токен из cookie
    auth_token = request.cookies.get('access_token')
    auth_header = request.headers.get('Authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        auth_token = auth_header.split(' ')[1]
    
    # Получаем погоду и курс валюты для отображения в шапке
    weather = {"temperature": "+20°"}
    currency = {"value": "69.8"}
    
    if auth_token:
        try:
            # Декодируем токен
            payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            
            if user_id:
                # Получаем данные пользователя из БД
                user = db.query(models.User).filter(models.User.id == user_id).first()
                
                if user:
                    print(f"DEBUG: Загружен пользователь: {user.email}, роль: {user.role}")
                    
                    # Получаем объявления пользователя с изображениями
                    try:
                        user_listings = db.query(models.Property).options(
                            joinedload(models.Property.images)
                        ).filter(models.Property.owner_id == user_id).all()
                        
                        # Форматируем объявления пользователя для шаблона
                        for prop in user_listings:
                            # Находим главное изображение или первое доступное
                            main_image = next((img for img in prop.images if img.is_main), None) or \
                                       (prop.images[0] if prop.images else None)
                            
                            formatted_user_listings.append({
                                "id": prop.id,
                                "title": prop.title,
                                "price": prop.price,
                                "address": prop.address,
                                "rooms": prop.rooms,
                                "area": prop.area,
                                "status": prop.status,
                                "notes": prop.notes,  # Дата съемки 360
                                "tour_360_url": prop.tour_360_url,
                                "has_tour": bool(prop.tour_360_url or prop.tour_360_file_id),  # Обновленная логика проверки
                                "image_url": get_valid_image_url(main_image.url if main_image else None)
                            })
                        
                        print(f"DEBUG: Найдено {len(formatted_user_listings)} объявлений пользователя")
                        
                    except Exception as e:
                        print(f"DEBUG: Ошибка при получении объявлений пользователя: {e}")
                    
                    # Получаем сохраненные объявления пользователя
                    try:
                        # Получаем идентификаторы сохраненных объявлений
                        favorites_query = db.query(models.Favorite).filter(models.Favorite.user_id == user_id).all()
                        saved_property_ids = [fav.property_id for fav in favorites_query]
                        
                        # Получаем сами объявления по ID с изображениями
                        if saved_property_ids:
                            saved_listings = db.query(models.Property).options(
                                joinedload(models.Property.images)
                            ).filter(
                                models.Property.id.in_(saved_property_ids)
                            ).all()
                            
                            # Форматируем сохраненные объявления для шаблона
                            for prop in saved_listings:
                                # Находим главное изображение или первое доступное
                                main_image = next((img for img in prop.images if img.is_main), None) or \
                                           (prop.images[0] if prop.images else None)
                                
                                formatted_saved_listings.append({
                                    "id": prop.id,
                                    "title": prop.title,
                                    "price": prop.price,
                                    "address": prop.address,
                                    "rooms": prop.rooms,
                                    "area": prop.area,
                                    "status": prop.status,
                                    "tour_360_url": prop.tour_360_url,
                                    "has_tour": bool(prop.tour_360_url or prop.tour_360_file_id),  # Обновленная логика проверки
                                    "image_url": get_valid_image_url(main_image.url if main_image else None)
                                })
                            
                            print(f"DEBUG: Найдено {len(saved_listings)} сохраненных объявлений")
                        else:
                            print("DEBUG: У пользователя нет избранных объявлений")
                    except Exception as e:
                        print(f"DEBUG: Ошибка при получении сохраненных объявлений: {e}")
        except Exception as e:
            print(f"DEBUG: Ошибка декодирования токена: {e}")
    
    # Если не удалось получить пользователя, перенаправляем на страницу авторизации
    if not user:
        return RedirectResponse('/mobile/auth', status_code=303)
    
    # Создаем расширенный объект пользователя для шаблона
    user_data = {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "is_active": user.is_active,
        "role": user.role.value if user.role else "USER",
        "created_at": user.created_at
    }
    
    # Определяем отображаемые данные в зависимости от роли
    if user.role == models.UserRole.COMPANY:
        user_data.update({
            "full_name": user.company_name or "Компания",
            "display_name": user.company_name or "Компания", 
            "company_name": user.company_name,
            "company_number": user.company_number,
            "company_owner": user.company_owner,
            "company_address": user.company_address,
            "company_description": user.company_description,
            "avatar_url": user.company_logo_url,
            "is_company": True
        })
    else:
        user_data.update({
            "full_name": user.full_name or f"Пользователь {user.id}",
            "display_name": user.full_name or f"Пользователь {user.id}",
            "avatar_url": None,
            "is_company": False
        })
    
    return templates.TemplateResponse(
        "layout/profile.html", 
        {
            "request": request, 
            "user": user_data, 
            "user_listings": formatted_user_listings, 
            "saved_listings": formatted_saved_listings,
            "active_tab": tab or "listings",
            "weather": weather,
            "currency": currency
        }
    )

@app.get("/mobile/create-listing", response_class=HTMLResponse, name="create_listing")
async def mobile_create_listing(request: Request, db: Session = Depends(deps.get_db)):
    # Получаем текущего пользователя
    user = None
    
    # Получаем токен из cookie
    auth_token = request.cookies.get('access_token')
    auth_header = request.headers.get('Authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        auth_token = auth_header.split(' ')[1]
    
    if auth_token:
        try:
            # Декодируем токен
            payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            
            if user_id:
                # Получаем данные пользователя из БД
                user = db.query(models.User).filter(models.User.id == user_id).first()
                print(f"DEBUG: Загружен пользователь для создания объявления: {user.email}, роль: {user.role}")
                
                # Дополняем данные пользователя для корпоративных аккаунтов
                if user and user.role == models.UserRole.COMPANY:
                    print(f"DEBUG: Корпоративный пользователь - {user.company_name}, владелец: {user.company_owner}")
                
        except Exception as e:
            print(f"DEBUG: Ошибка при проверке токена: {e}")
    
    # Проверяем, авторизован ли пользователь
    if not user:
        return RedirectResponse(url="/mobile/auth")
    
    return templates.TemplateResponse(
        "layout/create-listing.html",
        {
            "request": request,
            "user": user
        }
    )

@app.get("/mobile/search", response_class=HTMLResponse, name="search")
async def mobile_search(
    request: Request, 
    category: str = None, 
    price_min: int = None, 
    price_max: int = None, 
    min_area: float = None, 
    max_area: float = None,
    rooms: int = None,
    min_floor: int = None,
    max_floor: int = None,
    balcony: bool = None,
    furniture: bool = None,
    renovation: bool = None,
    parking: bool = None,
    q: str = None,
    db: Session = Depends(deps.get_db)
):
    print("\n===================================================")
    print("DEBUG: Параметры запроса:")
    print(f"  URL: {request.url}")
    print(f"  Поисковый запрос: {q}")
    print(f"  Категория: {category}")
    print(f"  Цена: {price_min} - {price_max}")
    print(f"  Площадь: {min_area} - {max_area}")
    print(f"  Комнаты: {rooms}")
    print(f"  Этаж: {min_floor} - {max_floor}")
    print(f"  Балкон: {balcony}, Мебель: {furniture}, Ремонт: {renovation}, Паркинг: {parking}")
    print("===================================================")
    
    # Если категория не указана, делаем "Недвижимость" активной по умолчанию
    if not category:
        category = "Недвижимость"
    
    # Формируем базовый запрос для получения активных объявлений
    query = db.query(models.Property).filter(models.Property.status == 'active')
    
    # Получаем все категории для выпадающего списка
    categories = db.query(models.Category).all()
    print(f"DEBUG: Загружены категории: {[cat.name for cat in categories]}")
    
    # Получаем общие категории товаров/услуг из JSON файла
    general_categories = load_categories_from_json()
    print(f"DEBUG: Загружены общие категории из JSON: {[cat['name'] for cat in general_categories]}")
    
    # Применяем фильтры, если они указаны
    if category and category != "Недвижимость":
        print(f"DEBUG: Применяем фильтр по категории: {category}")
        query = query.join(models.Property.categories).filter(models.Category.name == category)
    
    # Поиск по ключевому слову в названии или адресе
    if q:
        search_term = f"%{q}%"
        query = query.filter(or_(
            models.Property.title.ilike(search_term),
            models.Property.address.ilike(search_term),
            models.Property.description.ilike(search_term)
        ))
    
    # Фильтры по цене
    if price_min is not None:
        query = query.filter(models.Property.price >= price_min)
    
    if price_max is not None:
        query = query.filter(models.Property.price <= price_max)
    
    # Фильтры по площади
    if min_area is not None:
        query = query.filter(models.Property.area >= min_area)
    
    if max_area is not None:
        query = query.filter(models.Property.area <= max_area)
    
    # Фильтр по количеству комнат
    if rooms is not None:
        query = query.filter(models.Property.rooms == rooms)
    
    # Фильтры по этажу
    if min_floor is not None:
        query = query.filter(models.Property.floor >= min_floor)
    
    if max_floor is not None:
        query = query.filter(models.Property.floor <= max_floor)
    
    # Дополнительные фильтры
    if balcony is not None and balcony:
        query = query.filter(models.Property.has_balcony == True)
    
    if furniture is not None and furniture:
        query = query.filter(models.Property.has_furniture == True)
    
    if renovation is not None and renovation:
        query = query.filter(models.Property.has_renovation == True)
    
    if parking is not None and parking:
        query = query.filter(models.Property.has_parking == True)
    
    # Получаем объявления с загрузкой изображений
    properties_db = query.options(joinedload(models.Property.images)).all()
    
    # Форматируем данные для шаблона
    properties = []
    for prop in properties_db:
        # Находим главное изображение
        main_image = next((img for img in prop.images if img.is_main), None) or \
                   (prop.images[0] if prop.images else None)
        
        # Формируем массив URL изображений
        images = [get_valid_image_url(img.url) for img in prop.images] if prop.images else []
        
        properties.append({
            "id": prop.id,
            "title": prop.title,
            "price": prop.price,
            "address": prop.address,
            "rooms": prop.rooms,
            "area": prop.area,
            "floor": prop.floor,
            "building_floors": prop.building_floors,
            "has_tour": bool(prop.tour_360_url or prop.tour_360_file_id),
            "tour_360_url": prop.tour_360_url,
            "tour_360_file_id": prop.tour_360_file_id,
            "tour_360_optimized_url": prop.tour_360_optimized_url,
            "has_balcony": prop.has_balcony,
            "has_furniture": prop.has_furniture,
            "has_renovation": prop.has_renovation,
            "has_parking": prop.has_parking,
            "image_url": get_valid_image_url(main_image.url if main_image else None),
            "images": images,
            "images_count": len(images)
        })
    
    # Быстрые статичные значения для погоды и валют (убираю медленные API запросы)
    weather = {"temperature": "+20°"}
    currency = {"value": "87.5"}
    
    return templates.TemplateResponse("layout/search.html", {
        "request": request, 
        "properties": properties,
        "weather": weather,
        "currency": currency,
        "categories": categories,
        "general_categories": general_categories,  # Добавляем общие категории
        "selected_category": category,
        "q": q,
        "filter": {
            "category": category,
            "price_min": price_min,
            "price_max": price_max,
            "min_area": min_area,
            "max_area": max_area,
            "rooms": rooms,
            "min_floor": min_floor,
            "max_floor": max_floor,
            "balcony": balcony,
            "furniture": furniture,
            "renovation": renovation,
            "parking": parking
        }
    })

@app.get("/mobile/chats", response_class=HTMLResponse, name="chats")
async def mobile_chats(request: Request):
    return templates.TemplateResponse("layout/chats.html", {"request": request})

@app.get("/mobile/support", response_class=HTMLResponse, name="support")
async def mobile_support(request: Request):
    return templates.TemplateResponse("layout/support.html", {"request": request})

@app.get("/mobile/property/{property_id}", response_class=HTMLResponse, name="property")
async def mobile_property_detail(request: Request, property_id: int, db: Session = Depends(deps.get_db)):
    # Получаем текущего пользователя, если он авторизован
    current_user = None
    token = request.cookies.get('access_token')
    
    if token:
        try:
            payload = pyjwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = int(payload.get("sub"))
            current_user = db.query(models.User).filter(models.User.id == user_id).first()
        except Exception as e:
            print(f"DEBUG: Ошибка при получении пользователя: {e}")
    
    # Получаем объявление из БД
    property = db.query(models.Property).options(
        joinedload(models.Property.owner),
        joinedload(models.Property.images),
        joinedload(models.Property.categories)
    ).filter(models.Property.id == property_id).first()
    
    if not property:
        return templates.TemplateResponse("404.html", {"request": request})
    
    # Увеличиваем счетчик просмотров
    try:
        # Получаем IP адрес пользователя для защиты от накрутки
        client_ip = request.client.host
        
        # Увеличиваем счетчик только если:
        # 1. Пользователь не является владельцем объявления
        # 2. Объявление активно
        should_increment = True
        
        if current_user and property.owner_id == current_user.id:
            should_increment = False  # Владелец не учитывается в просмотрах
            print(f"DEBUG: Пропускаем увеличение просмотров - владелец объявления")
        
        if property.status != models.PropertyStatus.ACTIVE:
            should_increment = False  # Неактивные объявления не учитываются
            print(f"DEBUG: Пропускаем увеличение просмотров - объявление неактивно: {property.status}")
        
        if should_increment:
            property.views = (property.views or 0) + 1
            db.commit()
            print(f"DEBUG: Увеличен счетчик просмотров для объявления {property_id}: {property.views}")
        
    except Exception as e:
        print(f"DEBUG: Ошибка при увеличении счетчика просмотров: {e}")
        # Не прерываем выполнение, просто логируем ошибку
    
    # Проверяем, добавлено ли объявление в избранное
    is_favorite = False
    if current_user:
        favorite = db.query(models.Favorite).filter(
            models.Favorite.user_id == current_user.id,
            models.Favorite.property_id == property.id
        ).first()
        is_favorite = favorite is not None
    
    # Проверяем, является ли текущий пользователь владельцем
    is_owner = current_user and property.owner_id == current_user.id
    
    # Получаем первую категорию объявления (если есть)
    category = None
    if property.categories:
        category = property.categories[0]
    
    # Получаем похожие объявления (того же типа, в том же городе)
    similar_properties = db.query(models.Property).options(
        joinedload(models.Property.images)
    ).filter(
        models.Property.id != property.id,
        models.Property.city == property.city,
        models.Property.status == models.PropertyStatus.ACTIVE  # Используем enum вместо строки
    ).limit(5).all()
    
    # Форматируем похожие объявления
    similar_properties_data = []
    for prop in similar_properties:
        # Обработка изображений для похожих объявлений
        main_image_url = "/static/layout/assets/img/property-placeholder.jpg"
        
        # Сначала пробуем медиа-сервер
        if prop.images_data and isinstance(prop.images_data, list):
            for img_data in prop.images_data:
                if isinstance(img_data, dict) and "urls" in img_data:
                    main_image_url = img_data["urls"].get("medium", img_data["urls"].get("original", ""))
                    if img_data.get("is_main", False):
                        break  # Используем главное изображение
        
        # Если нет изображений с медиа-сервера, используем локальные
        elif prop.images:
            main_image = next((img for img in prop.images if img.is_main), None) or prop.images[0]
            if main_image:
                main_image_url = main_image.url
        
        similar_properties_data.append({
            "id": prop.id,
            "title": prop.title,
            "price": prop.price,
            "address": prop.address,
            "rooms": prop.rooms,
            "area": prop.area,
            "image_url": main_image_url
        })
    
    # Форматируем данные для шаблона
    property_data = {
        "id": property.id,
        "title": property.title,
        "description": property.description,
        "price": property.price,
        "address": property.address,
        "city": property.city,
        "area": property.area,
        "status": property.status.value.lower() if property.status else "draft",
        "is_featured": property.is_featured,
        "views": property.views or 0,  # Добавляем поле views
        "created_at": property.created_at.strftime("%d.%m.%Y") if property.created_at else None,  # Добавляем дату публикации
        "tour_360_url": property.tour_360_url,
        # Добавляем поля для загруженных 360° панорам
        "tour_360_file_id": property.tour_360_file_id,
        "tour_360_original_url": property.tour_360_original_url,
        "tour_360_optimized_url": property.tour_360_optimized_url,
        "tour_360_preview_url": property.tour_360_preview_url,
        "tour_360_thumbnail_url": property.tour_360_thumbnail_url,
        "tour_360_metadata": property.tour_360_metadata,
        "tour_360_uploaded_at": property.tour_360_uploaded_at,
        "has_360": bool(property.tour_360_url or property.tour_360_file_id),  # Добавляем поле has_360
        "rooms": property.rooms,
        "floor": property.floor,
        "building_floors": property.building_floors,
        "type": property.type or "apartment",
        "type_display": {
            "apartment": "Квартира",
            "house": "Дом", 
            "commercial": "Коммерческая",
            "land": "Участок"
        }.get(property.type or "apartment", "Квартира"),  # Правильное отображение типа
        "is_owner": is_owner,
        "notes": property.notes,
        "has_balcony": property.has_balcony,
        "has_furniture": property.has_furniture,
        "has_renovation": property.has_renovation,
        "has_parking": property.has_parking,
        "has_elevator": getattr(property, 'has_elevator', False),
        "owner": {
            "id": property.owner.id,
            "full_name": property.owner.full_name or "Неизвестен",
            "phone": property.owner.phone or "Не указан",
            "email": property.owner.email or "Не указан",
            "is_company": property.owner.role == models.UserRole.COMPANY if property.owner.role else False,
            "company_name": property.owner.company_name,
            "logo_url": property.owner.company_logo_url
        } if property.owner else None,
        "category": {
            "id": category.id,
            "name": category.name
        } if category else None,
        # Поддержка медиа-сервера
        "media_id": property.media_id,
        "images_data": property.images_data,
        # Координаты для карты
        "latitude": property.latitude,
        "longitude": property.longitude,
        "formatted_address": property.formatted_address,
    }
    
    # Обработка изображений: сначала пробуем медиа-сервер, потом локальные
    images_list = []
    
    # Если есть данные с медиа-сервера
    if property.images_data and isinstance(property.images_data, list):
        for img_data in property.images_data:
            if isinstance(img_data, dict) and "urls" in img_data:
                images_list.append({
                    "url": img_data["urls"].get("medium", img_data["urls"].get("original", "")),
                    "is_main": img_data.get("is_main", False),
                    "from_media_server": True
                })
    
    # Если есть media_id, но нет images_data, строим URL по media_id
    elif property.media_id:
        # Строим URL для изображений на основе media_id
        media_base_url = "https://wazir.kg/state"
        for i in range(1, 11):  # Проверяем до 10 изображений
            image_url = f"{media_base_url}/properties/{property.media_id}/image_{i}.jpg"
            images_list.append({
                "url": image_url,
                "is_main": i == 1,  # Первое изображение как главное
                "from_media_server": True
            })
            # Ограничиваемся 5 изображениями для отображения
            if i >= 5:
                break
    
    # Если нет изображений с медиа-сервера, используем локальные
    if not images_list and property.images:
        images_list = [{"url": img.url, "is_main": img.is_main, "from_media_server": False} for img in property.images]
    
    property_data["images"] = images_list
    
    # Получаем погоду и курс валюты для отображения в шапке
    weather = None
    currency = None
    try:
        # Здесь можно добавить вызов API для получения погоды и курса валюты
        # Для простоты используем заглушки
        weather = {"temperature": "+20°"}
        
        # Попробуем получить курс доллара к сому
        import requests
        try:
            # Используем публичный API для курса валют
            response = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
            if response.status_code == 200:
                data = response.json()
                kgs_rate = data.get("rates", {}).get("KGS", 87.5)
                currency = {"value": f"{kgs_rate:.1f}"}
            else:
                currency = {"value": "87.5"}  # Значение по умолчанию
        except:
            currency = {"value": "87.5"}  # Значение по умолчанию при ошибке
            
    except Exception as e:
        print(f"DEBUG: Ошибка при получении погоды или курса валюты: {e}")
        weather = {"temperature": "+20°"}
        currency = {"value": "87.5"}
    
    return templates.TemplateResponse("layout/property.html", {
        "request": request,
        "property": property_data,
        "similar_properties": similar_properties_data,
        "weather": weather,
        "currency": currency,
        "user": current_user,
        "is_favorite": is_favorite
    })

@app.get("/mobile/chat/{user_id}", response_class=HTMLResponse, name="chat")
async def mobile_chat(request: Request, user_id: int, db: Session = Depends(deps.get_db)):
    # Получаем property_id из query-параметров
    property_id = request.query_params.get("property_id")
    context = {"request": request, "user_id": user_id}
    
    if property_id:
        try:
            property_id = int(property_id)  # Преобразуем в число
            # Получаем информацию о объявлении, если указан property_id
            property_item = db.query(models.Property).filter(models.Property.id == property_id).first()
            if property_item:
                context["property"] = {
                    "id": property_item.id,
                    "title": property_item.title,
                    "price": property_item.price
                }
        except ValueError:
            # Обработка случая, когда property_id не является числом
            pass
    
    return templates.TemplateResponse("layout/chat.html", context)

# Тестовая страница для WebSocket
@app.get("/mobile/test-websocket", response_class=HTMLResponse)
async def test_websocket_page(request: Request):
    """Тестовая страница для проверки WebSocket соединений"""
    return templates.TemplateResponse("test_websocket.html", {"request": request})

@app.get("/mobile/test-media", response_class=HTMLResponse)
async def test_media_page(request: Request):
    """Тестовая страница для проверки медиа-сервера"""
    return templates.TemplateResponse("layout/test_media.html", {
        "request": request,
        "media_server": "https://wazir.kg/state"
    })

@app.post("/mobile/test-upload")
async def test_media_upload_mobile(
    request: Request,
    title: str = Form(...),
    photos: List[UploadFile] = File(...)
):
    """Тестовая загрузка изображений через мобильный интерфейс"""
    
    if not photos:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Проверяем файлы
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    for file in photos:
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file.content_type} not allowed"
            )
    
    # Используем медиа-загрузчик
    from app.utils.media_uploader import media_uploader
    
    result = await media_uploader.upload_property_images(photos)
    
    if result["status"] != "success":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return {
        "status": "success",
        "property_id": result.get("property_id"),
        "files_count": result.get("count", 0),
        "files": result.get("files", []),
        "message": f"Успешно загружено {result.get('count', 0)} файлов"
    }

# Создаем прямой API-роутер для отладки, который не использует аутентификацию
debug_router = APIRouter(prefix="/debug")

# Добавляем debug_router в приложение
app.include_router(debug_router)

# Добавляем маршруты отладки
@debug_router.get("/")
async def get_debug_info():
    """Получение отладочной информации"""
    return {
        "status": "debug_active",
        "timestamp": datetime.now().isoformat(),
        "routes": [
            "/debug/",
            "/debug/db-test"
        ]
    }

# API для получения курса валют
@app.get("/api/v1/currency")
async def get_currency_rate():
    """Получение актуального курса доллара к сому"""
    try:
        import requests
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        if response.status_code == 200:
            data = response.json()
            kgs_rate = data.get("rates", {}).get("KGS", 87.5)
            return {
                "success": True,
                "currency": "USD/KGS",
                "rate": round(kgs_rate, 1),
                "formatted": f"{kgs_rate:.1f}",
                "updated_at": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "currency": "USD/KGS", 
                "rate": 87.5,
                "formatted": "87.5",
                "error": "API недоступен"
            }
    except Exception as e:
        return {
            "success": False,
            "currency": "USD/KGS",
            "rate": 87.5, 
            "formatted": "87.5",
            "error": str(e)
        }

# API для чата
from pydantic import BaseModel

from app.models.chat import AppChatMessageModel
from typing import List, Optional, Dict, Any

class MessageReadRequest(BaseModel):
    message_id: int

@app.post("/api/v1/chat/messages/read")
async def mark_message_as_read(request: MessageReadRequest, db: Session = Depends(deps.get_db)):
    """ Маркировать сообщение как прочитанное """
    try:
        # В реальном приложении здесь был бы код для обновления сообщения в базе данных
        # Например: message = db.query(AppChatMessageModel).filter(AppChatMessageModel.id == request.message_id).first()
        # if message:
        #    message.is_read = True
        #    db.commit()
        print(f"DEBUG: Сообщение {request.message_id} отмечено как прочитанное")
        return {"status": "success", "message": f"Сообщение {request.message_id} отмечено как прочитанное"}
    except Exception as e:
        print(f"ERROR: Ошибка при маркировке сообщения как прочитанное: {e}")
        return {"status": "error", "message": f"Ошибка при маркировке сообщения: {str(e)}"}

# API для получения пользователя по ID
@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(deps.get_db)):
    """Получить информацию о пользователе по ID"""
    try:
        print(f"DEBUG: Запрос данных пользователя с ID {user_id}")
        
        # Получаем пользователя из базы данных
        user = db.query(models.User).filter(models.User.id == user_id).first()
        
        # Если пользователь найден, формируем ответ с его данными
        if user:
            print(f"DEBUG: Пользователь найден в БД: {user.email}, {user.full_name}, роль: {user.role}")
            
            # Определяем отображаемое имя в зависимости от роли
            if user.role == models.UserRole.COMPANY:
                display_name = user.company_name or user.full_name or "Компания"
                avatar_url = user.company_logo_url or f"/static/img/company{user_id}.png"
            else:
                display_name = user.full_name or f"Пользователь {user_id}"
                avatar_url = f"/static/img/avatar{user_id}.png"
            
            return {
                "id": user.id,
                "email": user.email,
                "full_name": display_name,
                "avatar": avatar_url,
                "status": "Онлайн" if user.is_active else "Не в сети",
                "is_active": user.is_active,
                "role": user.role.value if user.role else "USER",
                "company_name": user.company_name,
                "company_number": user.company_number,
                "phone": user.phone
            }
        else:
            print(f"DEBUG: Пользователь с ID {user_id} не найден в БД")
            # Если пользователь не найден, возвращаем стандартные данные
            return {
                "id": user_id,
                "email": f"user{user_id}@example.com",
                "full_name": f"User {user_id}",
                "avatar": f"/static/img/avatar{user_id}.png",
                "status": "Пользователь",
                "is_active": False,
                "role": "USER"
            }
    except Exception as e:
        print(f"ERROR: Ошибка при получении пользователя: {e}")
        # В случае ошибки возвращаем базовые данные
        return {
            "id": user_id,
            "email": f"user{user_id}@example.com",
            "full_name": f"User {user_id}",
            "avatar": f"/static/img/avatar{user_id}.png",
            "status": "Пользователь",
            "is_active": True,
            "role": "USER"
        }

# API для получения сообщений чата
@app.get("/api/v1/chat/messages/{user_id}")
async def get_chat_messages(user_id: int, request: Request, db: Session = Depends(deps.get_db)):
    """Получить сообщения чата с пользователем"""
    try:
        # Получаем текущего пользователя
        current_user = deps.get_current_user_optional(request, db)
        current_user_id = current_user.id if current_user else 0
        if current_user_id == 0:
            print("DEBUG: Не удалось определить текущего пользователя")
            return []
        
        # Используем импортированный chat_manager для доступа к сообщениям
        from app.websockets.chat_manager import manager as chat_manager
        
        # Формируем уникальный ID чата на основе идентификаторов пользователей
        chat_id = chat_manager.get_chat_id(current_user_id, user_id)
        print(f"DEBUG: Сформированный chat_id: {chat_id} для пользователей {current_user_id} и {user_id}")
        
        # Получаем сообщения из памяти chat_manager
        messages = chat_manager.chat_messages.get(chat_id, [])
        
        # Если сообщений нет в памяти, пробуем загрузить их из файла
        if not messages and os.path.exists("chat_messages.json"):
            try:
                with open("chat_messages.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # Сначала пробуем найти сообщения по новому chat_id
                    messages = data.get(chat_id, [])
                    
                    if not messages:
                        # Если сообщений нет, пробуем найти сообщения по старому chat_id="4"
                        # Это нужно для обратной совместимости со старыми сообщениями
                        old_messages = data.get("4", [])
                        
                        # Фильтруем сообщения, относящиеся к этим пользователям
                        filtered_messages = []
                        for msg in old_messages:
                            if (str(msg.get("sender_id")) == str(current_user_id) and str(msg.get("receiver_id")) == str(user_id)) or \
                               (str(msg.get("sender_id")) == str(user_id) and str(msg.get("receiver_id")) == str(current_user_id)):
                                # Обновляем chat_id для совместимости с новой системой
                                msg["chat_id"] = chat_id
                                filtered_messages.append(msg)
                        
                        # Используем отфильтрованные сообщения
                        messages = filtered_messages
                        
                        # Сохраняем обновленные сообщения в памяти chat_manager
                        if messages:
                            for msg in messages:
                                chat_manager.add_message_to_memory(chat_id, msg)
                    
                    print(f"DEBUG: Загружено {len(messages)} сообщений для чата {chat_id}")
                    # В случае, если мы мигрировали сообщения, сохраняем их в файл
                    chat_manager.save_messages_to_file()
            except Exception as e:
                print(f"DEBUG: Ошибка при загрузке сообщений из файла: {e}")
        
        print(f"DEBUG: Возвращаем {len(messages)} сообщений для чата с пользователем {user_id}")
        return messages
    except Exception as e:
        print(f"ERROR: Ошибка при получении сообщений чата: {e}")
        # Возвращаем пустой список, чтобы приложение продолжало работать
        return []

@app.get("/admin/login")
async def admin_login_get(request: Request):
    return templates.TemplateResponse("admin/index.html", {"request": request})

@app.post("/admin/login")
async def admin_login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    # Проверяем учетные данные администратора
    admin = db.query(models.User).filter(
        models.User.email == username,
        models.User.role == models.UserRole.ADMIN
    ).first()
    
    if not admin or not verify_password(password, admin.hashed_password):
        return templates.TemplateResponse(
            "admin/index.html",
            {"request": request, "error": "Неверный email или пароль"}
        )
    
    # Создаем токен для администратора
    access_token = create_access_token(
        data={"sub": str(admin.id), "is_admin": True}
    )
    
    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False,  # Позволяем JavaScript получить доступ к токену
        max_age=3600 * 24,  # Увеличиваем время жизни до 24 часов
        samesite="lax",
        path="/"  # Устанавливаем для всех путей
    )
    
    # Для отладки добавляем токен в URL первый раз
    return response

@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем доступ администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    # Получаем реальную статистику из БД
    total_users = db.query(models.User).count()
    
    # Общее количество объектов недвижимости
    total_properties = db.query(models.Property).count()
    
    # Количество объектов на модерации (заявки)
    pending_properties = db.query(models.Property).filter(models.Property.status == "pending").count()
    
    # Количество чатов
    total_chats = db.query(AppChatModel).count()
    
    # Для тикетов (обращений в техподдержку) используем примерное значение
    # В реальном приложении эти данные были бы получены из БД
    total_tickets = 13
    
    # Получаем последние 5 объектов недвижимости
    latest_properties_query = db.query(models.Property).options(
        joinedload(models.Property.owner),
        joinedload(models.Property.images)
    ).order_by(models.Property.created_at.desc()).limit(5).all()
    
    # Подготавливаем форматированные данные для отображения
    latest_properties = []
    
    status_display = {
        "draft": "Черновик",
        "pending": "На модерации",
        "active": "Активно",
        "rejected": "Отклонено",
        "sold": "Продано"
    }
    
    for prop in latest_properties_query:
        # Форматируем цену
        price = prop.price or 0
        
        # Определяем статус для отображения
        status_value = prop.status.value if prop.status else "draft"
        status = status_display.get(status_value, "Неизвестно")
        
        # Определяем тип объекта
        property_type = "sale"
        if hasattr(prop, 'property_type') and prop.property_type:
            property_type = prop.property_type.value
        
        property_type_display = {
            "sale": "Продажа",
            "rent": "Аренда"
        }.get(property_type, property_type)
        
        # Добавляем данные в массив
        latest_properties.append({
            "id": prop.id,
            "title": prop.title or f"Объект #{prop.id}",
            "price": price,
            "status": status_value,
            "status_display": status,
            "property_type": property_type,
            "property_type_display": property_type_display,
            "created_at": prop.created_at.isoformat() if prop.created_at else None,  # Конвертируем datetime в строку
        })
    
    # Рассчитываем динамические проценты изменений на основе имеющихся данных
    # В реальном приложении это можно было бы рассчитать сравнивая с предыдущим месяцем
    # Для примера используем ID как показатель роста
    
    # Делаем рост пользователей на основе ID последнего пользователя
    last_user_id = db.query(models.User.id).order_by(models.User.id.desc()).first()
    last_user_id = last_user_id[0] if last_user_id else 0
    users_change = round((last_user_id - total_users) / max(total_users, 1) * 100) if total_users > 0 else 0
    users_change = min(max(users_change, -99), 99)  # Ограничиваем диапазоном -99 до 99
    
    # Делаем рост объектов на основе ID последнего объекта
    last_property_id = db.query(models.Property.id).order_by(models.Property.id.desc()).first()
    last_property_id = last_property_id[0] if last_property_id else 0
    properties_change = round((last_property_id - total_properties) / max(total_properties, 1) * 100) if total_properties > 0 else 0
    properties_change = min(max(properties_change, -99), 99)  # Ограничиваем диапазоном -99 до 99
    
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "current_admin": user,  # Передаем данные администратора
            "total_users": total_users,
            "users_count": total_users,
            "users_change": users_change,
            "total_properties": total_properties,
            "properties_count": total_properties,
            "properties_change": properties_change,
            "total_chats": total_chats,
            "chats_change": total_chats,  # Используем количество чатов как динамический процент
            "requests_count": pending_properties,  # Заявки = объекты на модерации
            "requests_change": pending_properties,  # Используем количество заявок как динамический процент
            "tickets_count": total_tickets,  # Количество тикетов в техподдержку
            "tickets_change": -5,  # Примерное значение изменения
            "last_properties": latest_properties,
            "last_tickets": [],  # В данной версии не реализовано
        }
    )

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем доступ администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
        
    # Получаем только ОБЫЧНЫХ пользователей (исключаем администраторов)
    users = db.query(models.User).filter(models.User.role == models.UserRole.USER).all()
    
    # Подготавливаем данные для отображения
    enhanced_users = []
    
    for user_item in users:
        # Получаем количество объявлений пользователя
        properties_count = db.query(models.Property).filter(models.Property.owner_id == user_item.id).count()
        
        # Получаем количество объявлений с 360-турами
        tours_count = db.query(models.Property).filter(
            models.Property.owner_id == user_item.id,
            models.Property.tour_360_url.isnot(None),
            models.Property.tour_360_url != ""
        ).count()
        
        # Форматируем дату регистрации
        registered_at = "Нет данных"
        if hasattr(user_item, 'created_at') and user_item.created_at:
            registered_at = user_item.created_at.strftime("%Y-%m-%d %H:%M:%S")
        
        # Добавляем данные в массив
        enhanced_users.append({
            "id": user_item.id,
            "full_name": user_item.full_name if hasattr(user_item, 'full_name') and user_item.full_name else f"Пользователь {user_item.id}",
            "phone": user_item.phone if hasattr(user_item, 'phone') and user_item.phone else "Нет данных",
            "email": user_item.email if hasattr(user_item, 'email') and user_item.email else "Нет данных",
            "is_active": user_item.is_active if hasattr(user_item, 'is_active') else True,
            "properties_count": properties_count,
            "tours_count": tours_count,
            "registered_at": registered_at,
            "avatar_url": user_item.avatar_url if hasattr(user_item, 'avatar_url') and user_item.avatar_url else None,
        })
    
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "current_admin": user,  # Передаем данные текущего администратора
            "users": enhanced_users,
            "start_item": 1,
            "end_item": len(enhanced_users),
            "total_users": len(enhanced_users),
            "search_query": "",
            "status": None,
            "current_page": 1,
            "total_pages": 1,
            "pages": [1],
            "show_ellipsis": False,
        }
    )

@app.get("/admin/properties", response_class=HTMLResponse, name="admin_properties")
async def admin_properties(
    request: Request, 
    status: str = Query(None), 
    property_type: str = Query(None),
    search: str = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
        
    # Получаем категории для фильтра
    categories = db.query(models.Category).all()
    
    # Создаем базовый запрос к объектам недвижимости
    properties_query = db.query(models.Property).options(
        joinedload(models.Property.owner),
        joinedload(models.Property.images)
    )
    
    # Применяем фильтры
    if status:
        properties_query = properties_query.filter(models.Property.status == status)
    
    if property_type:
        try:
            property_type_id = int(property_type)
            # Фильтруем по категории через связь PropertyCategory
            properties_query = properties_query.join(models.PropertyCategory).filter(
                models.PropertyCategory.category_id == property_type_id
            )
        except (ValueError, TypeError):
            # Если property_type не число, фильтруем по типу объекта
            properties_query = properties_query.filter(models.Property.type == property_type)
            
    if search:
        search_term = f"%{search}%"
        properties_query = properties_query.filter(
            or_(
                models.Property.title.ilike(search_term),
                models.Property.address.ilike(search_term),
                models.Property.description.ilike(search_term)
            )
        )
    
    # Получаем общее количество объявлений
    total_properties = properties_query.count()
    
    # Пагинация
    items_per_page = 10
    total_pages = (total_properties + items_per_page - 1) // items_per_page if total_properties > 0 else 1
    
    # Проверяем корректность номера страницы
    if page > total_pages and total_pages > 0:
        page = total_pages
        
    # Применяем пагинацию
    start_idx = (page - 1) * items_per_page
    properties_paginated = properties_query.order_by(desc(models.Property.created_at)).offset(start_idx).limit(items_per_page).all()
    
    # Преобразуем объекты недвижимости в нужный формат
    properties_formatted = []
    
    for prop in properties_paginated:
        # Форматирование цены
        if prop.price:
            if prop.price >= 1000000:
                price_formatted = f"{prop.price/1000000:.1f} млн KGZ".replace('.0', '')
            else:
                price_formatted = f"{prop.price/1000:.1f} тыс KGZ".replace('.0', '')
        else:
            price_formatted = "Цена не указана"
        
        # Статус для отображения
        status_display_map = {
            'active': 'Активно',
            'pending': 'На проверке',
            'rejected': 'Отклонено',
            'draft': 'Черновик',
            'sold': 'Продано',
            'inactive': 'Неактивно'
        }
        status_display = status_display_map.get(prop.status, prop.status or 'Неизвестно')
        
        # Получаем информацию о владельце
        owner_name = prop.owner.full_name if prop.owner and prop.owner.full_name else "Пользователь"
        owner_email = prop.owner.email if prop.owner and prop.owner.email else ""
        
        # Получаем главное изображение
        main_image_url = "/static/images/default-property.jpg"
        all_images = []
        
        try:
            for img in prop.images:
                if img.url:
                    all_images.append({
                        'url': img.url,
                        'is_main': img.is_main
                    })
                    if img.is_main:
                        main_image_url = img.url
                        
            # Если нет главного изображения, берем первое
            if main_image_url == "/static/images/default-property.jpg" and all_images:
                main_image_url = all_images[0]['url']
                
        except Exception as e:
            print(f"Ошибка при получении изображений для объявления ID={prop.id}: {e}")
        
        # Получаем категорию
        category_info = None
        try:
            property_category = db.query(models.PropertyCategory).filter(
                models.PropertyCategory.property_id == prop.id
            ).first()
            
            if property_category:
                category = db.query(models.Category).filter(
                    models.Category.id == property_category.category_id
                ).first()
                if category:
                    category_info = {'name': category.name, 'id': category.id}
        except Exception as e:
            print(f"Ошибка при получении категории: {e}")
        
        # Проверяем наличие 360° тура
        has_tour = bool(getattr(prop, 'tour_360_url', None) or getattr(prop, 'tour_360_file_id', None))
        
        # Добавляем в список
        property_data = {
            'id': prop.id,
            'title': prop.title or f"Объект №{prop.id}",
            'address': prop.address or "Адрес не указан",
            'city': prop.city or "Бишкек",
            'description': prop.description or "",
            'price': prop.price or 0,
            'price_formatted': price_formatted,
            'area': prop.area,
            'rooms': prop.rooms,
            'floor': prop.floor,
            'building_floors': prop.building_floors,
            'bathroom_type': getattr(prop, 'bathroom_type', None),
            'type': prop.type or "apartment",
            'status': prop.status,
            'status_display': status_display,
            'views': getattr(prop, 'views', 0),
            'created_at': prop.created_at.isoformat() if prop.created_at else "",
            'owner_name': owner_name,
            'owner_email': owner_email,
            'owner_id': prop.owner_id,
            'image_url': main_image_url,
            'all_images': all_images,
            'category': category_info,
            'has_tour': has_tour,
            # Удобства
            'has_balcony': getattr(prop, 'has_balcony', False),
            'has_furniture': getattr(prop, 'has_furniture', False),
            'has_renovation': getattr(prop, 'has_renovation', False),
            'has_parking': getattr(prop, 'has_parking', False),
            'has_elevator': getattr(prop, 'has_elevator', False),
            'has_security': getattr(prop, 'has_security', False),
            'has_internet': getattr(prop, 'has_internet', False),
            'has_air_conditioning': getattr(prop, 'has_air_conditioning', False),
            'has_heating': getattr(prop, 'has_heating', False),
            'has_yard': getattr(prop, 'has_yard', False),
            'has_pool': getattr(prop, 'has_pool', False),
            'has_gym': getattr(prop, 'has_gym', False),
        }
        
        properties_formatted.append(property_data)
    
    # Вычисляем данные для пагинации
    start_item = start_idx + 1 if total_properties > 0 else 0
    end_item = min(start_idx + len(properties_formatted), total_properties)
    
    # Генерируем список страниц для навигации
    page_range = range(max(1, page - 2), min(total_pages + 1, page + 3))
    
    return templates.TemplateResponse("admin/properties.html", {
            "request": request,
        "current_admin": user,
        "properties": properties_formatted,
        "categories": categories,
        "status": status,
        "property_type": property_type,
        "search_query": search,
        "total_properties": total_properties,
            "total_pages": total_pages,
            "current_page": page,
            "pages": page_range,
            "start_item": start_item,
        "end_item": end_item
    })

# Функция для проверки доступа администратора
async def check_admin_access(request: Request, db: Session):
    auth_token = request.cookies.get('access_token')
    if not auth_token:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
            return RedirectResponse(url="/admin/login", status_code=303)
            
        # Проверяем, что пользователь является администратором
        if not payload.get("is_admin"):
            return RedirectResponse(url="/admin/login", status_code=303)
            
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return RedirectResponse(url="/admin/login", status_code=303)
            
        return user
    except Exception as e:
        print(f"DEBUG: Token validation error: {str(e)}")
        return RedirectResponse(url="/admin/login", status_code=303)

@app.get("/admin/requests", response_class=HTMLResponse, name="admin_requests")
async def admin_requests(request: Request, tab: str = Query('listings'), status: str = Query(None), 
                    property_type: str = Query(None), search: str = Query(None), 
                    page: int = Query(1, ge=1), db: Session = Depends(deps.get_db)):
    # Проверяем авторизацию и доступ администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    # Получаем все категории для фильтра
    categories = db.query(models.Category).all()
    
    # Получаем количество объявлений по типам
    try:
        # Для таба tours будем считать объявления с запросом на съемку 360
        tour_requests_count = db.query(models.Property).filter(
            models.Property.tour_360_url.like('%example.com%')
        ).count()
        
        # Для таба listings будем считать только объявления со статусом PENDING
        listing_requests_count = db.query(models.Property).filter(
            models.Property.status == 'pending'
        ).count()
    except Exception as e:
        print(f"Error counting properties: {e}")
        tour_requests_count = 0
        listing_requests_count = 0
    
    # Получаем список объявлений из БД
    try:
        # Создаем базовый запрос к таблице properties
        query = db.query(models.Property)\
            .join(models.User, models.Property.owner_id == models.User.id, isouter=True)\
            .options(
                joinedload(models.Property.owner),
                joinedload(models.Property.images)
            )
            
        # Фильтрация по типу объявления
        if tab == 'tours':
            # Для таба tours берем только принятые объявления с запросом на съемку 360
            query = query.filter(
                models.Property.tour_360_url.like('%example.com%'),
                models.Property.status.in_(['active', 'processing'])
            )
        elif tab == 'listings':
            # Для таба listings берем все объявления со статусом PENDING (на модерации)
            query = query.filter(
                models.Property.status == 'pending'
            )
            
        # Фильтрация по статусу, если указан
        if status:
            if status == 'new':
                query = query.filter(models.Property.status.in_(['new', 'pending']))
            else:
                status_map = {
                    'in_progress': 'processing',
                    'completed': 'active',
                    'rejected': 'rejected'
                }
                if status in status_map:
                    query = query.filter(models.Property.status == status_map[status])
        
        # Фильтрация по типу недвижимости, если указан
        if property_type:
            try:
                property_type_id = int(property_type)
                # Фильтруем по категории (связь с таблицей categories)
                query = query.join(models.PropertyCategory).filter(
                    models.PropertyCategory.category_id == property_type_id
                )
            except (ValueError, TypeError):
                # Если property_type не является числом, фильтруем по типу как обычно
                query = query.filter(models.Property.type == property_type)
        
        # Поиск
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    models.Property.title.ilike(search_term),
                    models.Property.description.ilike(search_term),
                    models.Property.address.ilike(search_term),
                    models.User.full_name.ilike(search_term)
                )
            )
        
        # Получаем общее количество записей после применения фильтров
        total_items = query.count()
        
        # Пагинация
        items_per_page = 10
        total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
        
        # Проверяем корректность номера страницы
        if page > total_pages and total_pages > 0:
            page = total_pages
            
        # Получаем данные с пагинацией
        start_idx = (page - 1) * items_per_page
        query = query.order_by(desc(models.Property.created_at)).offset(start_idx).limit(items_per_page)
        
        # Получаем объекты недвижимости
        properties = query.all()
        
        # Преобразуем в формат для шаблона
        requests_data = []
        
        # Маппинг статусов из БД в формат для шаблона
        status_map_reverse = {
            'new': 'new',
            'pending': 'new',
            'processing': 'in_progress',
            'active': 'completed',
            'rejected': 'rejected',
            'inactive': 'rejected'
        }
        
        for prop in properties:
            # Форматируем цену корректно
            if prop.price:
                if prop.price >= 1000000:
                    millions = prop.price / 1000000
                    price_formatted = f"{millions:.1f} млн KGZ".replace('.0', '')
                else:
                    thousands = prop.price / 1000
                    price_formatted = f"{thousands:.1f} тыс KGZ".replace('.0', '')
            else:
                price_formatted = "Цена не указана"
            
            # Определяем статус для отображения
            display_status = status_map_reverse.get(prop.status, 'new') if prop.status else 'new'
            
            # Получаем все изображения объявления
            property_images = []
            try:
                # Используем связанные изображения из SQLAlchemy
                for img in prop.images:
                    if img.url:
                        property_images.append({
                            'url': img.url,
                            'is_main': img.is_main
                        })
                
                # Если изображений нет, добавляем заглушку
                if not property_images:
                    property_images = []
                
            except Exception as e:
                print(f"Ошибка при получении изображений для объявления ID={prop.id}: {e}")
                property_images = []
            
            # Получаем информацию о владельце
            owner_data = {
                'id': prop.owner.id if prop.owner else None,
                'name': prop.owner.full_name if prop.owner and prop.owner.full_name else "Пользователь",
                'email': prop.owner.email if prop.owner and prop.owner.email else ""
            }
            
            # Получаем информацию о категории
            category_info = None
            try:
                # Получаем связь через PropertyCategory
                property_category = db.query(models.PropertyCategory).filter(
                    models.PropertyCategory.property_id == prop.id
                ).first()
                
                if property_category:
                    category = db.query(models.Category).filter(
                        models.Category.id == property_category.category_id
                    ).first()
                    if category:
                        category_info = {'name': category.name, 'id': category.id}
            except Exception as e:
                print(f"Ошибка при получении категории: {e}")
                category_info = None
            
            # Добавляем объект в список
            requests_data.append({
                'id': prop.id,
                'status': display_status,
                'created_at': prop.created_at.isoformat() if prop.created_at else None,  # Конвертируем datetime в строку
                'scheduled_date': prop.notes,  # Берем дату съемки из поля notes
                'property': {
                    'id': prop.id,
                    'title': prop.title or f"Объект №{prop.id}",
                    'address': prop.address or "Адрес не указан",
                    'price': prop.price or 0,
                    'price_formatted': price_formatted,
                    'type': prop.type or "apartment",
                    'images': property_images,  # Передаем все изображения
                    'category': category_info  # Добавляем информацию о категории
                },
                'user': owner_data
            })
            
        # Вычисляем начальный и конечный индексы для пагинации
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + len(requests_data), total_items)
        
    except Exception as e:
        print(f"Ошибка в получении заявок: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        requests_data = []
        total_items = 0
        total_pages = 1
        start_idx = 0
        end_idx = 0
    
    # Получаем параметры запроса для пагинации
    query_params = ""
    if tab:
        query_params += f"&tab={tab}"
    if status:
        query_params += f"&status={status}"
    if property_type:
        query_params += f"&property_type={property_type}"
    if search:
        query_params += f"&search={search}"
        
    # Генерируем список страниц для навигации
    page_range = range(max(1, page - 2), min(total_pages + 1, page + 3))
    
    return templates.TemplateResponse("admin/requests.html", {
        "request": request,
        "current_admin": user,
        "requests": requests_data,
        "tab": tab,
        "status": status,
        "property_type": property_type,
        "search": search,
        "categories": categories,  # Добавляем категории
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "pages": page_range,
        "start_item": start_idx + 1 if total_items > 0 else 0,
        "end_item": end_idx,
        "listing_requests_count": listing_requests_count,
        "tour_requests_count": tour_requests_count,
        "query_params": query_params
    })

@app.get("/admin/settings", response_class=HTMLResponse, name="admin_settings")
async def admin_settings(request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем доступ администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    class DummySettings:
        email_new_properties = False
        email_new_users = False
        push_notifications = False
        digest_frequency = 'never'
        color_scheme = 'orange'
        theme = 'light'
        compact_mode = False
        animations_enabled = True
    
    dummy_settings = DummySettings()
    return templates.TemplateResponse(
        "admin/settings.html",
        {"request": request, "current_admin": user, "settings": dummy_settings}
    )

# API для настроек
class SettingsModel(BaseModel):
    email_new_properties: Optional[bool] = True
    email_new_users: Optional[bool] = True
    push_notifications: Optional[bool] = False
    digest_frequency: Optional[str] = "daily"
    color_scheme: Optional[str] = "orange"
    theme: Optional[str] = "light"
    compact_mode: Optional[bool] = False
    animations_enabled: Optional[bool] = True

@app.post("/api/v1/settings")
async def save_settings(settings: SettingsModel, request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем авторизацию, но для этого API допускаем любого авторизованного пользователя
    auth_token = request.cookies.get('access_token')
    auth_header = request.headers.get('Authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        auth_token = auth_header.split(' ')[1]
    
    if not auth_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Требуется авторизация"})
    
    try:
        # Проверяем валидность токена
        payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
            return JSONResponse(status_code=401, content={"success": False, "error": "Токен истек"})
        
        # В реальном приложении здесь бы сохраняли настройки в БД
        # Для демонстрации просто возвращаем успех
        return {"success": True, "message": "Настройки сохранены успешно"}
    except Exception as e:
        print(f"DEBUG: Ошибка при сохранении настроек: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

# Сброс настроек
@app.post("/api/v1/settings/reset")
async def reset_settings(request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем авторизацию
    auth_token = request.cookies.get('access_token')
    auth_header = request.headers.get('Authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        auth_token = auth_header.split(' ')[1]
    
    if not auth_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Требуется авторизация"})
    
    try:
        # Проверяем валидность токена
        payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
            return JSONResponse(status_code=401, content={"success": False, "error": "Токен истек"})
        
        # В реальном приложении здесь бы сбрасывали настройки к значениям по умолчанию
        # Для демонстрации просто возвращаем успех
        return {"success": True, "message": "Настройки сброшены к значениям по умолчанию"}
    except Exception as e:
        print(f"DEBUG: Ошибка при сбросе настроек: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

# Функция для проверки доступа суперадмина
async def check_superadmin_access(request: Request, db: Session):
    auth_token = request.cookies.get('access_token')
    if not auth_token:
        return RedirectResponse(url="/superadmin/login", status_code=303)
    
    try:
        payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
            return RedirectResponse(url="/superadmin/login", status_code=303)
            
        # Проверяем, что пользователь является суперадминистратором
        if not payload.get("is_superadmin"):
            return RedirectResponse(url="/superadmin/login", status_code=303)
            
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return RedirectResponse(url="/superadmin/login", status_code=303)
            
        return user
    except Exception as e:
        print(f"DEBUG: SuperAdmin token validation error: {str(e)}")
        return RedirectResponse(url="/superadmin/login", status_code=303)

# ============================ SuperAdmin Routes ============================

@app.get("/superadmin/login")
async def superadmin_login_get(request: Request):
    return templates.TemplateResponse("superadmin/login.html", {"request": request})

@app.post("/superadmin/login")
async def superadmin_login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    # Проверяем учетные данные суперадмина
    # В реальном приложении должен быть отдельный статус суперадмина
    superadmin = db.query(models.User).filter(
        models.User.email == username,
        models.User.role == models.UserRole.ADMIN  # Временно используем роль ADMIN
    ).first()
    
    # Дополнительная проверка: только определенные email могут быть суперадминами
    superadmin_emails = ['superadmin@wazir.kg', 'admin@wazir.kg']
    
    if not superadmin or not verify_password(password, superadmin.hashed_password) or username not in superadmin_emails:
        return templates.TemplateResponse(
            "superadmin/login.html",
            {"request": request, "error": "Неверный логин или пароль суперадмина"}
        )
    
    # Создаем токен для суперадмина с флагом is_superadmin
    access_token = create_access_token(
        data={"sub": str(superadmin.id), "is_admin": True, "is_superadmin": True}
    )
    
    response = RedirectResponse(url="/superadmin/dashboard", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False,
        max_age=3600 * 24,
        samesite="lax",
        path="/"
    )
    
    return response

@app.get("/superadmin/logout")
async def superadmin_logout():
    response = RedirectResponse(url="/superadmin/login", status_code=303)
    response.delete_cookie("access_token", path="/")
    return response

@app.get("/superadmin", response_class=HTMLResponse)
@app.get("/superadmin/dashboard", response_class=HTMLResponse)
async def superadmin_dashboard(request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    # Получаем статистику
    from datetime import datetime, timedelta
    
    # Статистика
    stats = {
        'admins_count': db.query(models.User).filter(models.User.role == models.UserRole.ADMIN).count(),
        'users_count': db.query(models.User).filter(models.User.role == models.UserRole.USER).count(),
        'properties_count': db.query(models.Property).count(),
        'pending_requests': db.query(models.Property).filter(models.Property.status == 'PENDING').count()
    }
    
    # РЕАЛЬНЫЕ последние действия из БД
    recent_activities = []
    
    # Последние зарегистрированные пользователи (за последние 7 дней)
    week_ago = datetime.now() - timedelta(days=7)
    recent_users = db.query(models.User).filter(
        models.User.role == models.UserRole.USER,
        models.User.created_at >= week_ago
    ).order_by(desc(models.User.created_at)).limit(3).all()
    
    for user_item in recent_users:
        time_diff = datetime.now() - user_item.created_at
        if time_diff.days > 0:
            time_str = f"{time_diff.days} дн. назад"
        elif time_diff.seconds > 3600:
            time_str = f"{time_diff.seconds // 3600} ч. назад"
        else:
            time_str = f"{time_diff.seconds // 60} мин. назад"
            
        recent_activities.append({
            'icon': 'fas fa-user-plus',
            'action': f'Регистрация: {user_item.full_name or user_item.email}',
            'admin_name': 'Система',
            'time': time_str
        })
    
    # Последние объявления (за последние 3 дня)
    three_days_ago = datetime.now() - timedelta(days=3)
    recent_properties = db.query(models.Property).filter(
        models.Property.created_at >= three_days_ago
    ).order_by(desc(models.Property.created_at)).limit(2).all()
    
    for prop in recent_properties:
        time_diff = datetime.now() - prop.created_at
        if time_diff.days > 0:
            time_str = f"{time_diff.days} дн. назад"
        elif time_diff.seconds > 3600:
            time_str = f"{time_diff.seconds // 3600} ч. назад"
        else:
            time_str = f"{time_diff.seconds // 60} мин. назад"
            
        recent_activities.append({
            'icon': 'fas fa-building',
            'action': f'Новое объявление: {prop.title or f"Объект #{prop.id}"}',
            'admin_name': 'Пользователь',
            'time': time_str
        })
    
    # Последние изменения статусов объявлений
    recent_status_changes = db.query(models.Property).filter(
        models.Property.updated_at >= three_days_ago,
        models.Property.status.in_(['ACTIVE', 'REJECTED'])
    ).order_by(desc(models.Property.updated_at)).limit(2).all()
    
    for prop in recent_status_changes:
        time_diff = datetime.now() - prop.updated_at
        if time_diff.days > 0:
            time_str = f"{time_diff.days} дн. назад"
        elif time_diff.seconds > 3600:
            time_str = f"{time_diff.seconds // 3600} ч. назад"
        else:
            time_str = f"{time_diff.seconds // 60} мин. назад"
            
        status_text = "одобрено" if prop.status == 'ACTIVE' else "отклонено"
        recent_activities.append({
            'icon': 'fas fa-edit',
            'action': f'Объявление {status_text}: {prop.title or f"#{prop.id}"}',
            'admin_name': 'Модератор',
            'time': time_str
        })
    
    # Если нет реальных активностей, добавляем системное сообщение
    if not recent_activities:
        recent_activities.append({
            'icon': 'fas fa-info-circle',
            'action': 'Система запущена и работает стабильно',
            'admin_name': 'Система',
            'time': 'Сейчас'
        })
    
    # РЕАЛЬНЫЕ системные уведомления
    system_notifications = []
    
    # Проверяем наличие объявлений на модерации
    pending_count = db.query(models.Property).filter(models.Property.status == 'PENDING').count()
    if pending_count > 0:
        system_notifications.append({
            'icon': 'fas fa-exclamation-triangle',
            'title': 'Требуется модерация',
            'message': f'{pending_count} объявлений ожидают модерации',
            'color': '#f59e0b',
            'bg_color': '#fefbf3',
            'time': 'Сейчас'
        })
    
    # Проверяем новых пользователей за последние 24 часа
    yesterday = datetime.now() - timedelta(days=1)
    new_users_count = db.query(models.User).filter(
        models.User.created_at >= yesterday,
        models.User.role == models.UserRole.USER
    ).count()
    
    if new_users_count > 0:
        system_notifications.append({
            'icon': 'fas fa-users',
            'title': 'Новые пользователи',
            'message': f'{new_users_count} новых пользователей за последние 24 часа',
            'color': '#10b981',
            'bg_color': '#f0fdf4',
            'time': '24 часа'
        })
    
    # Проверяем неактивных администраторов
    inactive_admins = db.query(models.User).filter(
        models.User.role == models.UserRole.ADMIN,
        models.User.is_active == False
    ).count()
    
    if inactive_admins > 0:
        system_notifications.append({
            'icon': 'fas fa-user-slash',
            'title': 'Неактивные администраторы',
            'message': f'{inactive_admins} администраторов неактивны',
            'color': '#ef4444',
            'bg_color': '#fef2f2',
            'time': '1 час назад'
        })
    
    # Проверяем количество активных объявлений
    active_properties = db.query(models.Property).filter(models.Property.status == 'ACTIVE').count()
    if active_properties > 100:
        system_notifications.append({
            'icon': 'fas fa-chart-line',
            'title': 'Высокая активность',
            'message': f'{active_properties} активных объявлений в системе',
            'color': '#10b981',
            'bg_color': '#f0fdf4',
            'time': 'Сейчас'
        })
    
    # Если нет уведомлений, добавляем позитивное сообщение
    if not system_notifications:
        system_notifications.append({
            'icon': 'fas fa-check-circle',
            'title': 'Все в порядке',
            'message': 'Система работает стабильно, проблем не обнаружено',
            'color': '#10b981',
            'bg_color': '#f0fdf4',
            'time': 'Сейчас'
        })
    
    # РЕАЛЬНАЯ системная информация
    system_info = {
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'fastapi_version': '0.104.1',
        'memory_usage': f"{psutil.virtual_memory().percent:.1f}%" if psutil else "Недоступно",
        'uptime': 'Online'
    }
    
    # Пытаемся получить реальную информацию о системе
    if psutil:
        try:
            # Использование CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            # Использование памяти
            memory = psutil.virtual_memory()
            # Использование диска
            disk = psutil.disk_usage('/')
            
            system_info.update({
                'cpu_usage': f"{cpu_percent:.1f}%",
                'memory_usage': f"{memory.percent:.1f}%",
                'memory_total': f"{memory.total // (1024**3)} GB",
                'disk_usage': f"{disk.percent:.1f}%",
                'disk_free': f"{disk.free // (1024**3)} GB"
            })
        except Exception as e:
            print(f"DEBUG: Ошибка получения системной информации: {e}")
    
    return templates.TemplateResponse(
        "superadmin/dashboard.html",
        {
            "request": request,
            "current_user": user,
            "stats": stats,
            "recent_activities": recent_activities,
            "system_notifications": system_notifications,
            "system_info": system_info
        }
    )

@app.get("/superadmin/admins", response_class=HTMLResponse)
async def superadmin_admins(request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    # Получаем всех администраторов (ADMIN и MANAGER роли)
    admins = db.query(models.User).filter(
        or_(
            models.User.role == models.UserRole.ADMIN,
            models.User.role == models.UserRole.MANAGER
        )
    ).all()
    
    # Подсчитываем статистику
    admins_total = len(admins)
    admins_active = len([admin for admin in admins if admin.is_active])
    admins_inactive = admins_total - admins_active
    
    # Подготавливаем данные для отображения
    enhanced_admins = []
    for admin in admins:
        enhanced_admins.append({
            "id": admin.id,
            "full_name": admin.full_name,
            "email": admin.email,
            "phone": admin.phone,
            "is_active": admin.is_active,
            "avatar_url": getattr(admin, 'avatar_url', None),
            "created_at": admin.created_at.isoformat() if admin.created_at else None,  # Конвертируем datetime в строку
        })
    
    # Добавляем переменные пагинации (даже если пагинация не нужна)
    total_pages = 1
    current_page = 1
    per_page = len(enhanced_admins)
    total_items = len(enhanced_admins)
    
    return templates.TemplateResponse(
        "superadmin/admins.html",
        {
            "request": request,
            "current_user": user,
            "admins": enhanced_admins,
            "admins_total": admins_total,
            "admins_active": admins_active,
            "admins_inactive": admins_inactive,
            "total_pages": total_pages,
            "current_page": current_page,
            "per_page": per_page,
            "total_items": total_items
        }
    )

@app.get("/superadmin/users", response_class=HTMLResponse)
async def superadmin_users(
    request: Request, 
    search: str = Query(None),
    status: str = Query(None),
    property_filter: str = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    # Базовый запрос
    query = db.query(models.User).filter(models.User.role == models.UserRole.USER)
    
    # Применяем фильтры
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                models.User.full_name.ilike(search_term),
                models.User.email.ilike(search_term),
                models.User.phone.ilike(search_term)
            )
        )
    
    if status:
        if status == "active":
            query = query.filter(models.User.is_active == True)
        elif status == "blocked":
            query = query.filter(models.User.is_active == False)
    
    # Пагинация
    total_items = query.count()
    items_per_page = 50
    total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
    
    if page > total_pages and total_pages > 0:
        page = total_pages
    
    start_idx = (page - 1) * items_per_page
    users_results = query.order_by(desc(models.User.created_at)).offset(start_idx).limit(items_per_page).all()
    
    # Подготавливаем данные для отображения
    enhanced_users = []
    for u in users_results:
        properties_count = db.query(models.Property).filter(models.Property.owner_id == u.id).count()
        
        # Применяем фильтр по недвижимости после получения данных
        if property_filter:
            if property_filter == "with" and properties_count == 0:
                continue
            elif property_filter == "without" and properties_count > 0:
                continue
        
        enhanced_users.append({
            "id": u.id,
            "full_name": u.full_name or f"Пользователь {u.id}",
            "phone": u.phone or "Нет данных",
            "email": u.email or "Нет данных",
            "is_active": u.is_active,
            "properties_count": properties_count,
            "registered_at": u.created_at.isoformat() if u.created_at else None,  # Конвертируем datetime в строку
        })
    
    # Параметры запроса для пагинации
    query_params = ""
    if search:
        query_params += f"&search={search}"
    if status:
        query_params += f"&status={status}"
    if property_filter:
        query_params += f"&property_filter={property_filter}"
    
    start_item = start_idx + 1 if len(enhanced_users) > 0 else 0
    end_item = start_idx + len(enhanced_users)
    page_range = range(max(1, page - 2), min(total_pages + 1, page + 3))
    
    return templates.TemplateResponse(
        "superadmin/users.html",
        {
            "request": request,
            "current_user": user,
            "users": enhanced_users,
            "total_items": total_items,
            "items_per_page": items_per_page,
            "current_page": page,
            "total_pages": total_pages,
            "start_item": start_item,
            "end_item": end_item,
            "page_range": page_range,
            "query_params": query_params,
            "search": search or "",
            "status": status or "",
            "property_filter": property_filter or ""
        }
    )

@app.get("/superadmin/companies", response_class=HTMLResponse)
async def superadmin_companies(
    request: Request, 
    search: str = Query(None),
    status: str = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    from sqlalchemy.orm import joinedload
    from sqlalchemy import or_
    
    items_per_page = 20
    offset = (page - 1) * items_per_page
    
    # Базовый запрос для компаний (пользователи с ролью COMPANY)
    query = db.query(models.User).filter(models.User.role == models.UserRole.COMPANY)
    
    # Применяем фильтры
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                models.User.full_name.ilike(search_term),
                models.User.email.ilike(search_term),
                models.User.phone.ilike(search_term),
                models.User.company_name.ilike(search_term),
                models.User.company_number.ilike(search_term),
                models.User.company_owner.ilike(search_term)
            )
        )
    
    if status:
        if status == "active":
            query = query.filter(models.User.is_active == True)
        elif status == "blocked":
            query = query.filter(models.User.is_active == False)
    
    # Подсчет общего количества для пагинации
    total_items = query.count()
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    # Получаем компании с пагинацией
    companies_results = query.offset(offset).limit(items_per_page).all()
    
    # Формируем данные для шаблона
    enhanced_companies = []
    total_company_properties = 0
    
    for company in companies_results:
        properties_count = db.query(models.Property).filter(models.Property.owner_id == company.id).count()
        total_company_properties += properties_count
        
        enhanced_companies.append({
            "id": company.id,
            "company_name": company.company_name,
            "company_number": company.company_number,
            "company_owner": company.company_owner,
            "company_logo_url": company.company_logo_url,
            "company_description": company.company_description,
            "company_address": company.company_address,
            "full_name": company.full_name,
            "email": company.email,
            "phone": company.phone,
            "is_active": company.is_active,
            "properties_count": properties_count,
            "created_at": company.created_at.isoformat() if company.created_at else None,  # Конвертируем datetime в строку
        })
    
    # Статистика
    companies_total = query.count()
    companies_active = query.filter(models.User.is_active == True).count()
    companies_inactive = companies_total - companies_active
    
    return templates.TemplateResponse(
        "superadmin/companies.html",
        {
            "request": request,
            "current_user": user,
            "companies": enhanced_companies,
            "companies_total": companies_total,
            "companies_active": companies_active,
            "companies_inactive": companies_inactive,
            "total_company_properties": total_company_properties,
            "search": search or "",
            "status": status or "",
            "current_page": page,
            "total_pages": total_pages,
        }
    )

@app.get("/superadmin/properties", response_class=HTMLResponse)
async def superadmin_properties(
    request: Request, 
    search: str = Query(None),
    status: str = Query(None),
    property_type: str = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    from sqlalchemy.orm import joinedload
    from sqlalchemy import or_, desc
    
    items_per_page = 20
    offset = (page - 1) * items_per_page
    
    # Базовый запрос для объявлений
    query = db.query(models.Property).options(joinedload(models.Property.owner))
    
    # Применяем фильтры
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                models.Property.title.ilike(search_term),
                models.Property.address.ilike(search_term),
                models.Property.description.ilike(search_term)
            )
        )
    
    if status:
        if status == "active":
            query = query.filter(models.Property.status == 'ACTIVE')
        elif status == "pending":
            query = query.filter(models.Property.status == 'PENDING')
        elif status == "rejected":
            query = query.filter(models.Property.status == 'REJECTED')
        elif status == "draft":
            query = query.filter(models.Property.status == 'DRAFT')
    
    if property_type:
        # Фильтр по типу недвижимости - здесь можно добавить логику фильтрации
        pass
    
    # Сортировка по дате создания (новые сначала)
    query = query.order_by(desc(models.Property.created_at))
    
    # Подсчет общего количества для пагинации
    total_items = query.count()
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    # Получаем объявления с пагинацией
    properties_results = query.offset(offset).limit(items_per_page).all()
    
    # Формируем данные для шаблона
    enhanced_properties = []
    
    for prop in properties_results:
        # Форматирование цены
        price_formatted = f"{int(prop.price):,} сом".replace(",", " ") if prop.price else "Не указана"
        
        # Получаем имя владельца
        owner_name = "Неизвестен"
        if prop.owner:
            if prop.owner.role == models.UserRole.COMPANY:
                owner_name = prop.owner.company_name or prop.owner.full_name or prop.owner.email
            else:
                owner_name = prop.owner.full_name or prop.owner.email
        
        # URL изображения (если есть)
        image_url = "/static/img/property-placeholder.jpg"  # Дефолтное изображение
        if hasattr(prop, 'images') and prop.images:
            # prop.images - это список объектов PropertyImage, получаем URL первого изображения
            first_image = prop.images[0]
            if hasattr(first_image, 'url'):
                image_url = first_image.url
        
        enhanced_properties.append({
            "id": prop.id,
            "title": prop.title or f"Объект #{prop.id}",
            "address": prop.address or "Адрес не указан",
            "price": prop.price or 0,
            "price_formatted": price_formatted,
            "rooms": prop.rooms,
            "area": prop.area,
            "status": prop.status.value.lower() if prop.status else "draft",
            "status_display": {
                "active": "Активно",
                "pending": "На модерации", 
                "rejected": "Отклонено",
                "draft": "Черновик"
            }.get(prop.status.value.lower() if prop.status else "draft", "Неизвестно"),
            "owner_id": prop.owner_id,
            "owner_name": owner_name,
            "image_url": image_url,
            "created_at": prop.created_at.isoformat() if prop.created_at else None,  # Конвертируем datetime в строку
        })
    
    # Статистика
    total_properties = db.query(models.Property).count()
    active_count = db.query(models.Property).filter(models.Property.status == 'ACTIVE').count()
    pending_count = db.query(models.Property).filter(models.Property.status == 'PENDING').count()
    rejected_count = db.query(models.Property).filter(models.Property.status == 'REJECTED').count()
    
    return templates.TemplateResponse(
        "superadmin/properties.html",
        {
            "request": request,
            "current_user": user,
            "properties": enhanced_properties,
            "total_properties": total_properties,
            "active_count": active_count,
            "pending_count": pending_count,
            "rejected_count": rejected_count,
            "search": search or "",
            "status": status or "",
            "property_type": property_type or "",
            "current_page": page,
            "total_pages": total_pages,
        }
    )

@app.get("/superadmin/logs", response_class=HTMLResponse)
async def superadmin_logs(request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    return templates.TemplateResponse(
        "superadmin/logs.html",
        {
            "request": request,
            "current_user": user,
        }
    )

@app.get("/superadmin/analytics", response_class=HTMLResponse)
async def superadmin_analytics(request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    from datetime import datetime, timedelta
    from sqlalchemy import func, extract
    
    # Статистика пользователей
    total_users = db.query(models.User).filter(models.User.role == models.UserRole.USER).count()
    active_users = db.query(models.User).filter(
        models.User.role == models.UserRole.USER,
        models.User.is_active == True
    ).count()
    
    # Статистика объявлений
    total_properties = db.query(models.Property).count()
    active_properties = db.query(models.Property).filter(models.Property.status == 'ACTIVE').count()
    pending_properties = db.query(models.Property).filter(models.Property.status == 'PENDING').count()
    
    # Статистика по дням за последние 30 дней
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Регистрации пользователей по дням
    users_by_date = db.query(
        func.date(models.User.created_at).label('date'),
        func.count(models.User.id).label('count')
    ).filter(
        models.User.created_at >= start_date,
        models.User.role == models.UserRole.USER
    ).group_by(
        func.date(models.User.created_at)
    ).order_by('date').all()
    
    # Объявления по дням
    properties_by_date = db.query(
        func.date(models.Property.created_at).label('date'),
        func.count(models.Property.id).label('count')
    ).filter(
        models.Property.created_at >= start_date
    ).group_by(
        func.date(models.Property.created_at)
    ).order_by('date').all()
    
    # Популярные категории
    try:
        popular_categories = db.query(
            models.Category.name.label('category'),
            func.count(models.PropertyCategory.property_id).label('count')
        ).join(
            models.PropertyCategory, models.Category.id == models.PropertyCategory.category_id
        ).group_by(
            models.Category.id, models.Category.name
        ).order_by(
            func.count(models.PropertyCategory.property_id).desc()
        ).limit(10).all()
    except:
        popular_categories = []
    
    # Средняя цена по категориям
    try:
        price_by_category = db.query(
            models.Category.name.label('category'),
            func.avg(models.Property.price).label('avg_price')
        ).join(
            models.PropertyCategory, models.Category.id == models.PropertyCategory.category_id
        ).join(
            models.Property, models.PropertyCategory.property_id == models.Property.id
        ).filter(
            models.Property.price.isnot(None),
            models.Property.price > 0
        ).group_by(
            models.Category.id, models.Category.name
        ).order_by('avg_price').all()
    except:
        price_by_category = []
    
    # Статистика активности по месяцам
    monthly_stats = db.query(
        extract('month', models.Property.created_at).label('month'),
        func.count(models.Property.id).label('count')
    ).filter(
        models.Property.created_at >= datetime.now().replace(month=1, day=1)
    ).group_by(
        extract('month', models.Property.created_at)
    ).order_by('month').all()
    
    # Топ пользователи по количеству объявлений
    top_users = db.query(
        models.User.id,
        models.User.full_name,
        models.User.email,
        func.count(models.Property.id).label('properties_count')
    ).join(
        models.Property, models.User.id == models.Property.owner_id
    ).filter(
        models.User.role == models.UserRole.USER
    ).group_by(
        models.User.id, models.User.full_name, models.User.email
    ).order_by(
        func.count(models.Property.id).desc()
    ).limit(10).all()
    
    # Форматируем данные для графиков
    users_chart_data = {
        'labels': [item.date.strftime('%d.%m') for item in users_by_date[-14:]] or [],
        'data': [item.count for item in users_by_date[-14:]] or []
    }
    
    properties_chart_data = {
        'labels': [item.date.strftime('%d.%m') for item in properties_by_date[-14:]] or [],
        'data': [item.count for item in properties_by_date[-14:]] or []
    }
    
    categories_chart_data = {
        'labels': [item.category for item in popular_categories[:6]] or ['Нет данных'],
        'data': [item.count for item in popular_categories[:6]] or [0]
    }
    
    price_chart_data = {
        'labels': [item.category for item in price_by_category[:6]] or ['Нет данных'],
        'data': [float(item.avg_price) if item.avg_price else 0 for item in price_by_category[:6]] or [0]
    }
    
    # Месяцы на русском
    month_names = {
        1: 'Янв', 2: 'Фев', 3: 'Мар', 4: 'Апр', 5: 'Май', 6: 'Июн',
        7: 'Июл', 8: 'Авг', 9: 'Сен', 10: 'Окт', 11: 'Ноя', 12: 'Дек'
    }
    
    monthly_chart_data = {
        'labels': [month_names.get(int(item.month), f'Месяц {item.month}') for item in monthly_stats] or ['Нет данных'],
        'data': [item.count for item in monthly_stats] or [0]
    }
    
    return templates.TemplateResponse(
        "superadmin/analytics.html",
        {
            "request": request,
            "current_user": user,
            "total_users": total_users,
            "active_users": active_users,
            "total_properties": total_properties,
            "active_properties": active_properties,
            "pending_properties": pending_properties,
            "users_chart_data": users_chart_data,
            "properties_chart_data": properties_chart_data,
            "categories_chart_data": categories_chart_data,
            "price_chart_data": price_chart_data,
            "monthly_chart_data": monthly_chart_data,
            "top_users": top_users,
            "popular_categories": popular_categories
        }
    )

@app.get("/superadmin/settings", response_class=HTMLResponse)
async def superadmin_settings(request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    return templates.TemplateResponse("superadmin/settings.html", {
        "request": request,
        "current_user": user
    })

# API роуты для суперадмина
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@app.post("/api/v1/superadmin/admins")
async def create_admin(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    password: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    try:
        # Проверяем уникальность email
        existing_email = db.query(models.User).filter(models.User.email == email).first()
        if existing_email:
            return JSONResponse(status_code=400, content={"success": False, "message": "Пользователь с таким email уже существует"})
        
        # Проверяем уникальность телефона (если указан)
        if phone:
            existing_phone = db.query(models.User).filter(models.User.phone == phone).first()
            if existing_phone:
                return JSONResponse(status_code=400, content={"success": False, "message": "Пользователь с таким телефоном уже существует"})
        
        # Хешируем пароль
        hashed_password = pwd_context.hash(password)
        
        # Создаем нового администратора
        new_admin = models.User(
            email=email,
            full_name=full_name,
            phone=phone,
            hashed_password=hashed_password,
            role=models.UserRole.ADMIN,
            is_active=True
        )
        
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        print(f"DEBUG: Создан новый администратор: {email}")
        return JSONResponse(content={"success": True, "message": "Администратор создан успешно"})
        
    except Exception as e:
        print(f"ERROR: Ошибка создания администратора: {e}")
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": f"Ошибка создания: {str(e)}"})

@app.get("/api/v1/superadmin/admins/{admin_id}")
async def get_admin(
    admin_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=401, content={"success": False, "message": "Доступ запрещен"})
    
    admin = db.query(models.User).filter(
        models.User.id == admin_id,
        models.User.role == models.UserRole.ADMIN
    ).first()
    
    if not admin:
        return JSONResponse(status_code=404, content={"success": False, "message": "Администратор не найден"})
    
    return JSONResponse(content={
        "success": True,
        "admin": {
            "id": admin.id,
            "full_name": admin.full_name,
            "email": admin.email,
            "phone": admin.phone,
            "is_active": admin.is_active
        }
    })

@app.put("/api/v1/superadmin/admins/{admin_id}")
async def update_admin(
    admin_id: int,
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    is_active: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=401, content={"success": False, "message": "Доступ запрещен"})
    
    try:
        admin = db.query(models.User).filter(
            models.User.id == admin_id,
            models.User.role == models.UserRole.ADMIN
        ).first()
        
        if not admin:
            return JSONResponse(status_code=404, content={"success": False, "message": "Администратор не найден"})
        
        # Обновляем данные
        admin.full_name = full_name
        admin.email = email
        admin.phone = phone
        admin.is_active = is_active.lower() == 'true'
        
        db.commit()
        
        return JSONResponse(content={"success": True, "message": "Администратор обновлен успешно"})
        
    except Exception as e:
        print(f"ERROR: Ошибка обновления администратора: {e}")
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": f"Ошибка обновления: {str(e)}"})

@app.delete("/api/v1/superadmin/admins/{admin_id}")
async def delete_admin(
    admin_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=401, content={"success": False, "message": "Доступ запрещен"})
    
    try:
        # Проверяем, что это не сам суперадмин пытается удалить себя
        if admin_id == user.id:
            return JSONResponse(content={"success": False, "message": "Нельзя удалить самого себя"})
        
        admin = db.query(models.User).filter(
            models.User.id == admin_id,
            models.User.role == models.UserRole.ADMIN
        ).first()
        
        if not admin:
            return JSONResponse(status_code=404, content={"success": False, "message": "Администратор не найден"})
        
        db.delete(admin)
        db.commit()
        
        return JSONResponse(content={"success": True, "message": "Администратор удален успешно"})
        
    except Exception as e:
        print(f"ERROR: Ошибка удаления администратора: {e}")
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": f"Ошибка удаления: {str(e)}"})

@app.get("/api/v1/superadmin/stats")
async def get_superadmin_stats(request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=401, content={"success": False, "message": "Доступ запрещен"})
    
    try:
        stats = {
            'admins_count': db.query(models.User).filter(models.User.role == models.UserRole.ADMIN).count(),
            'users_count': db.query(models.User).count(),
            'properties_count': db.query(models.Property).count(),
            'pending_requests': db.query(models.Property).filter(models.Property.status == 'PENDING').count()
        }
        
        return JSONResponse(content={"success": True, "stats": stats})
        
    except Exception as e:
        print(f"ERROR: Ошибка получения статистики: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": f"Ошибка: {str(e)}"})

# Дополнительные API роуты для суперадмина

@app.get("/api/v1/superadmin/users/{user_id}")
async def get_superadmin_user(
    user_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=401, content={"success": False, "message": "Доступ запрещен"})
    
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not target_user:
        return JSONResponse(status_code=404, content={"success": False, "message": "Пользователь не найден"})
    
    # Получаем объявления пользователя
    properties = db.query(models.Property).filter(models.Property.owner_id == user_id).all()
    properties_data = [{
        "id": prop.id,
        "title": prop.title,
        "address": prop.address,
        "price": prop.price
    } for prop in properties]
    
    return JSONResponse(content={
        "success": True,
        "user": {
            "id": target_user.id,
            "full_name": target_user.full_name,
            "email": target_user.email,
            "phone": target_user.phone,
            "is_active": target_user.is_active,
            "properties_count": len(properties_data),
            "registered_at": target_user.created_at.isoformat() if target_user.created_at else None,  # Конвертируем datetime в строку
            "properties": properties_data
        }
    })

@app.delete("/api/v1/superadmin/users/{user_id}/properties")
async def delete_user_properties(
    user_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=401, content={"success": False, "message": "Доступ запрещен"})
    
    try:
        # Получаем все объявления пользователя
        properties = db.query(models.Property).filter(models.Property.owner_id == user_id).all()
        
        if not properties:
            return JSONResponse(content={"success": False, "message": "У пользователя нет объявлений"})
        
        # Удаляем все объявления
        for prop in properties:
            db.delete(prop)
        
        db.commit()
        
        return JSONResponse(content={"success": True, "message": f"Удалено {len(properties)} объявлений"})
        
    except Exception as e:
        print(f"ERROR: Ошибка удаления объявлений пользователя: {e}")
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": f"Ошибка удаления: {str(e)}"})

@app.post("/api/v1/superadmin/users/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=401, content={"success": False, "message": "Доступ запрещен"})
    
    try:
        target_user = db.query(models.User).filter(models.User.id == user_id).first()
        
        if not target_user:
            return JSONResponse(status_code=404, content={"success": False, "message": "Пользователь не найден"})
        
        # Переключаем статус
        target_user.is_active = not target_user.is_active
        db.commit()
        
        status_text = "активирован" if target_user.is_active else "заблокирован"
        return JSONResponse(content={"success": True, "message": f"Пользователь {status_text}"})
        
    except Exception as e:
        print(f"ERROR: Ошибка изменения статуса пользователя: {e}")
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": f"Ошибка изменения статуса: {str(e)}"})

# Дополнительные API роуты для управления объявлениями

@app.get("/api/v1/superadmin/properties/{property_id}")
async def get_superadmin_property(
    property_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=401, content={"success": False, "message": "Доступ запрещен"})
    
    property_item = db.query(models.Property).filter(models.Property.id == property_id).first()
    
    if not property_item:
        return JSONResponse(status_code=404, content={"success": False, "message": "Объявление не найдено"})
    
    return JSONResponse(content={
        "success": True,
        "property": {
            "id": property_item.id,
            "title": property_item.title,
            "price": property_item.price,
            "address": property_item.address,
            "status": property_item.status.value if property_item.status else "draft",
            "rooms": property_item.rooms,
            "area": property_item.area
        }
    })

@app.put("/api/v1/superadmin/properties/{property_id}")
async def update_superadmin_property(
    property_id: int,
    request: Request,
    title: str = Form(...),
    price: float = Form(...),
    address: str = Form(...),
    status: str = Form(...),
    rooms: int = Form(None),
    area: float = Form(None),
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ суперадмина
    user = await check_superadmin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=401, content={"success": False, "message": "Доступ запрещен"})
    
    try:
        property_item = db.query(models.Property).filter(models.Property.id == property_id).first()
        
        if not property_item:
            return JSONResponse(status_code=404, content={"success": False, "message": "Объявление не найдено"})
        
        # Обновляем данные
        property_item.title = title
        property_item.price = price
        property_item.address = address
        property_item.status = status
        if rooms is not None:
            property_item.rooms = rooms
        if area is not None:
            property_item.area = area
        
        db.commit()
        
        return JSONResponse(content={"success": True, "message": "Объявление обновлено успешно"})
        
    except Exception as e:
        print(f"ERROR: Ошибка обновления объявления: {e}")
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": f"Ошибка обновления: {str(e)}"})

# ============================ Admin Services Routes ============================

@app.get("/admin/services", response_class=HTMLResponse, name="admin_services")
async def admin_services(request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем доступ администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    # Получаем все категории сервисов с подсчетом карточек
    try:
        categories_raw = db.query(ServiceCategory).all()
        categories = []
        
        for cat in categories_raw:
            # Подсчитываем количество карточек в категории
            try:
                cards_count = db.query(ServiceCard).filter(ServiceCard.category_id == cat.id).count()
            except:
                cards_count = 0
                
            categories.append({
                'id': cat.id,
                'title': cat.title,
                'slug': cat.slug,
                'is_active': cat.is_active,
                'created_at': cat.created_at,
                'cards_count': cards_count
            })
            
    except Exception as e:
        print(f"DEBUG: Ошибка получения категорий: {e}")
        # Если таблицы не созданы, создаем тестовые категории
        categories = [
            {
                'id': 1,
                'title': 'Рестораны',
                'slug': 'restaurants',
                'is_active': True,
                'created_at': None,
                'cards_count': 0
            },
            {
                'id': 2,
                'title': 'Кафе',
                'slug': 'cafes',
                'is_active': True,
                'created_at': None,
                'cards_count': 0
            }
        ]
    
    return templates.TemplateResponse("admin/services.html", {
        "request": request,
        "current_admin": user,
        "categories": categories
    })

@app.get("/admin/services/categories/{category_id}/cards", response_class=HTMLResponse, name="admin_service_cards")
async def admin_service_cards(request: Request, category_id: int, db: Session = Depends(deps.get_db)):
    # Проверяем доступ администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    # Получаем категорию
    try:
        category = db.query(ServiceCategory).filter(ServiceCategory.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Категория не найдена")
    except Exception as e:
        print(f"DEBUG: Ошибка получения категории: {e}")
        # Если таблицы не созданы, создаем фиктивную категорию для тестирования
        category = type('Category', (), {
            'id': category_id,
            'title': f'Категория {category_id}',
            'slug': f'category-{category_id}',
            'is_active': True
        })()
    
    # Получаем все карточки в данной категории С ИЗОБРАЖЕНИЯМИ
    try:
        from sqlalchemy.orm import joinedload
        service_cards_raw = db.query(ServiceCard).options(
            joinedload(ServiceCard.images)
        ).filter(ServiceCard.category_id == category_id).all()
    except Exception as e:
        print(f"DEBUG: Ошибка получения карточек: {e}")
        # Если таблицы не созданы, возвращаем пустой список
        service_cards_raw = []
    
    # Преобразуем карточки в сериализуемый формат
    service_cards = []
    for card in service_cards_raw:
        service_cards.append({
            "id": card.id,
            "title": card.title,
            "description": card.description,
            "address": card.address,
            "phone": card.phone,
            "email": card.email,
            "website": card.website,
            "image_url": card.image_url,
            "is_active": card.is_active,
            "images": [{"url": img.url, "is_main": img.is_main} for img in card.images],  # ЗАГРУЖАЕМ РЕАЛЬНЫЕ ИЗОБРАЖЕНИЯ
            "has_360_tour": card.has_360_tour(),  # ПРОВЕРЯЕМ НАЛИЧИЕ 360° ТУРА
            "created_at": card.created_at,
            "photos_count": len(card.images)  # ДОБАВЛЯЕМ КОЛИЧЕСТВО ФОТОГРАФИЙ
        })
    
    return templates.TemplateResponse("admin/service_cards.html", {
        "request": request,
        "current_admin": user,
        "category": category,
        "service_cards": service_cards
    })

# API для создания категории сервисов
@app.post("/api/v1/admin/service-categories")
async def create_service_category(
    request: Request,
    title: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=403, content={"success": False, "error": "Доступ запрещен"})
    
    try:
        # Создаем slug из title
        slug = title.lower().replace(' ', '-').replace('ь', '').replace('ъ', '')
        # Удаляем спецсимволы и заменяем кириллицу на латиницу
        slug_mapping = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ы': 'y', 'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        
        for cyrillic, latin in slug_mapping.items():
            slug = slug.replace(cyrillic, latin)
        
        # Проверяем уникальность slug
        existing = db.query(ServiceCategory).filter(ServiceCategory.slug == slug).first()
        counter = 1
        original_slug = slug
        while existing:
            slug = f"{original_slug}-{counter}"
            existing = db.query(ServiceCategory).filter(ServiceCategory.slug == slug).first()
            counter += 1
        
        # Создаем категорию
        category = ServiceCategory(
            title=title,
            slug=slug,
            is_active=True
        )
        
        db.add(category)
        db.commit()
        db.refresh(category)
        
        return {"success": True, "message": "Категория создана успешно", "category": {
            "id": category.id,
            "title": category.title,
            "slug": category.slug,
            "is_active": category.is_active
        }}
        
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Ошибка при создании категории: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

# API для редактирования категории сервисов
@app.put("/api/v1/admin/service-categories/{category_id}")
async def update_service_category(
    category_id: int,
    request: Request,
    title: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=403, content={"success": False, "error": "Доступ запрещен"})
    
    try:
        # Находим категорию
        category = db.query(ServiceCategory).filter(ServiceCategory.id == category_id).first()
        if not category:
            return JSONResponse(status_code=404, content={"success": False, "error": "Категория не найдена"})
        
        category.title = title
        db.commit()
        
        return {"success": True, "message": "Категория обновлена успешно"}
        
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Ошибка при обновлении категории: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

# API для удаления категории сервисов
@app.delete("/api/v1/admin/service-categories/{category_id}")
async def delete_service_category(
    category_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=403, content={"success": False, "error": "Доступ запрещен"})
    
    try:
        # Находим категорию
        category = db.query(ServiceCategory).filter(ServiceCategory.id == category_id).first()
        if not category:
            return JSONResponse(status_code=404, content={"success": False, "error": "Категория не найдена"})
        
        # Удаляем связанные карточки
        db.query(ServiceCard).filter(ServiceCard.category_id == category_id).delete()
        
        # Удаляем категорию
        db.delete(category)
        db.commit()
        
        return {"success": True, "message": "Категория удалена успешно"}
        
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Ошибка при удалении категории: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

# API для создания карточки заведения
@app.post("/api/v1/admin/service-cards")
async def create_service_card(
    request: Request,
    category_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    address: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    website: str = Form(""),
    latitude: float = Form(None),
    longitude: float = Form(None),
    tour_360_url: str = Form(""),
    images: List[UploadFile] = File(default=[]),
    tour_360_file: UploadFile = File(None),
    db: Session = Depends(deps.get_db)
):
    # Проверяем доступ администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=403, content={"success": False, "error": "Доступ запрещен"})
    
    try:
        # Проверяем существование категории
        category = db.query(ServiceCategory).filter(ServiceCategory.id == category_id).first()
        if not category:
            return JSONResponse(status_code=404, content={"success": False, "error": "Категория не найдена"})
        
        # Создаем карточку заведения
        service_card = ServiceCard(
            category_id=category_id,
            title=title,
            description=description or None,
            address=address or None,
            phone=phone or None,
            email=email or None,
            website=website or None,
            latitude=latitude,
            longitude=longitude,
            tour_360_url=tour_360_url or None,
            is_active=True
        )
        
        db.add(service_card)
        db.commit()
        db.refresh(service_card)
        
        # Обрабатываем загруженные изображения
        if images and len(images) > 0 and images[0].filename:
            try:
                from app.utils.media_uploader import media_uploader
                
                # Загружаем изображения на медиа-сервер БЕЗ УКАЗАНИЯ property_id
                # Медиа-сервер сам сгенерирует ID и вернет готовые URLs
                upload_result = await media_uploader.upload_property_images(images)
                
                if upload_result.get("status") == "success" and upload_result.get("count", 0) > 0:
                    uploaded_count = upload_result["count"]
                    images_data = upload_result["files"]
                    print(f"DEBUG: Успешно загружено {uploaded_count} изображений на медиа-сервер")
                    
                    # Создаем записи в БД для каждого загруженного изображения
                    for i, file_info in enumerate(images_data):
                        # Берем medium URL как основной - КАК В ОТДЕЛЬНОЙ ЗАГРУЗКЕ
                        image_url = file_info["urls"]["medium"]
                        
                        service_image = ServiceCardImage(
                            service_card_id=service_card.id,
                            url=image_url,
                            is_main=(i == 0)  # Первое фото главное
                        )
                        db.add(service_image)
                        
                        # Если это первое изображение, устанавливаем его как основное
                        if i == 0:
                            service_card.image_url = image_url
                    
                    # Обновляем дату последней загрузки фотографий
                    service_card.photos_uploaded_at = datetime.now()
                    db.commit()
                    print(f"DEBUG: Сохранено {len(images_data)} изображений в БД")
                else:
                    print(f"ERROR: Ошибка загрузки на медиа-сервер: {upload_result.get('message', 'Неизвестная ошибка')}")
                    
            except Exception as e:
                print(f"DEBUG: Ошибка при загрузке изображений на медиа-сервер: {str(e)}")
                import traceback
                print(f"DEBUG: Полная ошибка: {traceback.format_exc()}")
        
        # Обрабатываем 360° панораму
        if tour_360_file and tour_360_file.filename:
            try:
                from app.utils.panorama_processor import PanoramaProcessor
                
                processor = PanoramaProcessor()
                
                # Удаление существующих файлов панорамы, если они есть
                if service_card.tour_360_file_id:
                    try:
                        await processor.delete_panorama_files(service_card.tour_360_file_id, str(service_card.id))
                    except Exception as e:
                        print(f"Ошибка удаления существующих файлов: {str(e)}")
                
                # Обработка панорамы (используем card_id как property_id)
                result = await processor.upload_panorama(tour_360_file, service_card.id)
                
                if not result.get('success'):
                    return JSONResponse(status_code=500, content={"success": False, "error": "Ошибка при загрузке панорамы"})
                
                service_card.tour_360_file_id = result.get('file_id')
                service_card.tour_360_original_url = result['urls'].get('original')
                service_card.tour_360_optimized_url = result['urls'].get('optimized')
                service_card.tour_360_preview_url = result['urls'].get('preview')
                service_card.tour_360_thumbnail_url = result['urls'].get('thumbnail')
                service_card.tour_360_metadata = json.dumps(result.get('metadata', {}), ensure_ascii=False)
                service_card.tour_360_uploaded_at = datetime.now()
                
                service_card.tour_360_url = None
                
                db.commit()
                db.refresh(service_card)
                
                response_data = {
                    "success": True,
                    "message": "360° панорама успешно загружена и обработана",
                    "file_id": result.get('file_id'),
                    "urls": result['urls'],
                    "metadata": result.get('metadata', {}),
                    "uploaded_at": datetime.now().isoformat()
                }
                
                return JSONResponse(content=response_data)
                
            except Exception as e:
                print(f"DEBUG: Ошибка при загрузке 360° панорамы: {str(e)}")
        
        return {"success": True, "message": "Карточка заведения создана успешно", "service_card": {
            "id": service_card.id,
            "title": service_card.title,
            "description": service_card.description,
            "address": service_card.address,
            "phone": service_card.phone,
            "email": service_card.email,
            "website": service_card.website,
            "latitude": service_card.latitude,
            "longitude": service_card.longitude,
            "image_url": service_card.image_url,
            "is_active": service_card.is_active
        }}
        
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Ошибка при создании карточки: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

# API для загрузки 360° панорамы заведения (файл)
@app.post("/api/v1/admin/service-cards/{card_id}/360/upload")
async def upload_service_card_360_file(
    card_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db)
):
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=403, content={"success": False, "error": "Доступ запрещен"})
    
    try:
        service_card = db.query(ServiceCard).filter(ServiceCard.id == card_id).first()
        if not service_card:
            return JSONResponse(status_code=404, content={"success": False, "error": "Заведение не найдено"})
        
        if not file.content_type or not file.content_type.startswith('image/'):
            return JSONResponse(status_code=400, content={"success": False, "error": "Файл должен быть изображением"})
        
        from app.utils.panorama_processor import panorama_processor
        
        result = await panorama_processor.upload_panorama(file, card_id)
        
        if not result.get("success"):
            error_message = result.get("message", "Ошибка при загрузке панорамы")
            return JSONResponse(status_code=500, content={"success": False, "error": error_message})
        
        service_card.tour_360_file_id = result['file_id']
        service_card.tour_360_original_url = result['urls']['original']
        service_card.tour_360_optimized_url = result['urls']['optimized']
        service_card.tour_360_preview_url = result['urls']['preview']
        service_card.tour_360_thumbnail_url = result['urls']['thumbnail']
        service_card.tour_360_metadata = json.dumps(result['metadata'], ensure_ascii=False)
        service_card.tour_360_uploaded_at = datetime.now()
        service_card.tour_360_url = None
        
        db.commit()
        db.refresh(service_card)
        
        return JSONResponse(content={
            "success": True,
            "message": "360° панорама успешно загружена и обработана",
            "file_id": result['file_id'],
            "urls": result['urls'],
            "metadata": result['metadata'],
            "uploaded_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: Ошибка при загрузке 360° панорамы: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

# API для сохранения 360° панорамы заведения (URL) - для обратной совместимости
@app.post("/api/v1/admin/service-cards/{card_id}/360")
async def save_service_card_360_url(
    card_id: int,
    request: Request,
    tour_360_url: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """Сохранение 360° панорамы для заведения (URL)"""
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=403, content={"success": False, "error": "Доступ запрещен"})
    
    try:
        # Находим карточку заведения
        service_card = db.query(ServiceCard).filter(ServiceCard.id == card_id).first()
        if not service_card:
            return JSONResponse(status_code=404, content={"success": False, "error": "Заведение не найдено"})
        
        # Сохраняем URL и очищаем файловые поля
        service_card.tour_360_url = tour_360_url
        service_card.tour_360_file_id = None
        service_card.tour_360_original_url = None
        service_card.tour_360_optimized_url = None
        service_card.tour_360_preview_url = None
        service_card.tour_360_thumbnail_url = None
        service_card.tour_360_metadata = None
        service_card.tour_360_uploaded_at = datetime.now()
        
        db.commit()
        
        return {"success": True, "message": "360° панорама успешно сохранена"}
        
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Ошибка при сохранении 360°: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

# API для получения информации о 360° панораме и фотографиях заведения
@app.get("/api/v1/admin/service-cards/{card_id}/media")
async def get_service_card_media_info(
    card_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    """Получение информации о медиафайлах заведения"""
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=403, content={"success": False, "error": "Доступ запрещен"})
    
    try:
        # Находим карточку заведения с изображениями
        service_card = db.query(ServiceCard).options(
            joinedload(ServiceCard.images)
        ).filter(ServiceCard.id == card_id).first()
        
        if not service_card:
            return JSONResponse(status_code=404, content={"success": False, "error": "Заведение не найдено"})
        
        # Информация о фотографиях
        photos_info = {
            "count": len(service_card.images),
            "last_uploaded": service_card.photos_uploaded_at.isoformat() if service_card.photos_uploaded_at else None,
            "photos": [{"url": img.url, "is_main": img.is_main} for img in service_card.images]
        }
        
        # Информация о 360° панораме
        tour_360_info = {
            "has_tour": service_card.has_360_tour(),
            "file_id": service_card.tour_360_file_id,
            "url": service_card.tour_360_url,
            "optimized_url": service_card.tour_360_optimized_url,
            "last_uploaded": service_card.tour_360_uploaded_at.isoformat() if service_card.tour_360_uploaded_at else None,
            "type": "file" if service_card.tour_360_file_id else ("url" if service_card.tour_360_url else None)
        }
        
        return {
            "success": True,
            "photos": photos_info,
            "tour_360": tour_360_info
        }
        
    except Exception as e:
        print(f"ERROR: Ошибка при получении медиа-информации: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

# API для загрузки фотографий заведения
@app.post("/api/v1/admin/service-cards/{card_id}/photos")
async def upload_service_card_photos(
    card_id: int,
    photos: List[UploadFile] = File(...),
    db: Session = Depends(deps.get_db)
):
    """Загрузка фотографий для заведения - точная копия логики недвижимости"""
    try:
        print("=== ЗАГРУЗКА ФОТОГРАФИЙ ЗАВЕДЕНИЯ ===")
        print(f"Card ID: {card_id}, файлов: {len(photos)}")
        
        # Проверяем что заведение существует
        service_card = db.query(ServiceCard).filter(ServiceCard.id == card_id).first()
        if not service_card:
            return JSONResponse(status_code=404, content={"success": False, "error": "Заведение не найдено"})
        
        # Проверяем фотографии - ТОЧНО КАК В НЕДВИЖИМОСТИ
        if not photos or len(photos) < 2:
            return JSONResponse(status_code=400, content={
                "success": False, 
                "message": "Необходимо загрузить минимум 2 фотографии"
            })
        
        # Проверяем типы файлов - ТОЧНО КАК В НЕДВИЖИМОСТИ
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
        for photo in photos:
            if photo.content_type not in allowed_types:
                return JSONResponse(status_code=400, content={
                    "success": False,
                    "message": f"Неподдерживаемый тип файла: {photo.content_type}"
                })
        
        # Загружаем изображения на медиа-сервер - ТОЧНО КАК В НЕДВИЖИМОСТИ (БЕЗ ВТОРОГО ПАРАМЕТРА!)
        print("DEBUG: Загрузка изображений на медиа-сервер...")
        from app.utils.media_uploader import media_uploader
        upload_result = await media_uploader.upload_property_images(photos)
        
        print(f"DEBUG: Результат загрузки: {upload_result}")
        
        if upload_result["status"] != "success":
            return JSONResponse(status_code=400, content={
                "success": False,
                "message": f"Ошибка загрузки изображений: {upload_result['message']}"
            })
        
        property_media_id = upload_result["property_id"]
        images_data = upload_result["files"]
        
        print(f"DEBUG: Изображения загружены, media_id: {property_media_id}")
        
        # Удаляем старые изображения из БД
        old_images = db.query(ServiceCardImage).filter(ServiceCardImage.service_card_id == card_id).all()
        for old_image in old_images:
            db.delete(old_image)
        print(f"DEBUG: Удалено {len(old_images)} старых изображений")
        
        uploaded_images = []
        # Создаем записи в БД для каждого загруженного изображения
        for i, file_info in enumerate(images_data):
            # Берем medium URL как основной
            image_url = file_info["urls"]["medium"]
            
            print(f"DEBUG: Создаем запись для изображения: {image_url}")
            
            service_image = ServiceCardImage(
                service_card_id=card_id,
                url=image_url,
                is_main=(i == 0)  # Первое изображение - основное
            )
            db.add(service_image)
            uploaded_images.append(image_url)
            
            # Если это первое изображение, обновляем основное изображение заведения
            if i == 0:
                service_card.image_url = image_url
                print(f"DEBUG: Установлено основное изображение: {image_url}")
        
        # Обновляем дату загрузки фотографий
        from datetime import datetime
        service_card.photos_uploaded_at = datetime.utcnow()
        
        db.commit()
        print(f"DEBUG: Сохранено {len(uploaded_images)} изображений в БД")
        print("=== ЗАГРУЗКА ЗАВЕРШЕНА УСПЕШНО ===")
        
        return {
            "success": True,
            "message": f"Успешно загружено {len(images_data)} фотографий",
            "count": len(images_data),
            "images": uploaded_images,
            "media_id": property_media_id
        }
            
    except Exception as e:
        db.rollback()
        print(f"ОШИБКА: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@app.post("/mobile/test-debug-upload")
async def test_debug_upload(
    request: Request,
    title: str = Form(...),
    photos: List[UploadFile] = File(...)
):
    """Тестовый эндпоинт для отладки загрузки файлов"""
    try:
        print(f"DEBUG: Получено {len(photos)} файлов для отладочной загрузки")
        
        # Подготавливаем файлы для отправки
        files_data = []
        for i, file in enumerate(photos):
            file_content = await file.read()
            file_size = len(file_content)
            print(f"DEBUG: Файл {i+1}: {file.filename}, размер: {file_size} байт, тип: {file.content_type}")
            
            files_data.append(
                ("images", (file.filename, file_content, file.content_type))
            )
            # Сбрасываем указатель файла
            await file.seek(0)
        
        # Генерируем test property_id
        import uuid
        test_property_id = f"test-{uuid.uuid4().hex[:8]}"
        
        # Отправляем на отладочный PHP-скрипт
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"DEBUG: Отправляем на https://wazir.kg/state/debug_upload.php")
            response = await client.post(
                "https://wazir.kg/state/debug_upload.php",
                files=files_data,
                data={"property_id": test_property_id}
            )
            
            print(f"DEBUG: Получен ответ со статусом: {response.status_code}")
            print(f"DEBUG: Тело ответа: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "status": "success",
                    "debug_result": result,
                    "files_sent": len(photos),
                    "test_property_id": test_property_id
                }
            else:
                return {
                    "status": "error",
                    "message": f"Debug upload failed with status {response.status_code}",
                    "response": response.text
                }
                
    except Exception as e:
        print(f"ERROR: Ошибка при отладочной загрузке: {str(e)}")
        return {
            "status": "error",
            "message": f"Debug upload error: {str(e)}"
        }

@app.get("/mobile/test-debug", response_class=HTMLResponse)
async def test_debug_page(request: Request):
    return templates.TemplateResponse("mobile/test_debug.html", {"request": request})

@app.put("/api/v1/admin/service-cards/{card_id}")
async def update_service_card(
    card_id: int,
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    address: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    website: str = Form(""),
    is_active: bool = Form(True),
    db: Session = Depends(deps.get_db)
):
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=403, content={"success": False, "error": "Доступ запрещен"})
    
    try:
        service_card = db.query(ServiceCard).filter(ServiceCard.id == card_id).first()
        if not service_card:
            return JSONResponse(status_code=404, content={"success": False, "error": "Заведение не найдено"})
        
        service_card.title = title
        service_card.description = description or None
        service_card.address = address or None
        service_card.phone = phone or None
        service_card.email = email or None
        service_card.website = website or None
        service_card.is_active = is_active
        
        db.commit()
        
        return {"success": True, "message": "Заведение успешно обновлено"}
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: Ошибка при обновлении заведения: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

@app.delete("/api/v1/admin/service-cards/{card_id}")
async def delete_service_card(
    card_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=403, content={"success": False, "error": "Доступ запрещен"})
    
    try:
        service_card = db.query(ServiceCard).filter(ServiceCard.id == card_id).first()
        if not service_card:
            return JSONResponse(status_code=404, content={"success": False, "error": "Заведение не найдено"})
        
        db.query(ServiceCardImage).filter(ServiceCardImage.service_card_id == card_id).delete()
        
        try:
            from app.utils.media_uploader import media_uploader
            service_media_id = f"service-{card_id}"
            delete_result = await media_uploader.delete_property_images(service_media_id)
            print(f"DEBUG: Результат удаления с медиа-сервера: {delete_result}")
        except Exception as e:
            print(f"WARNING: Ошибка при удалении изображений с медиа-сервера: {str(e)}")
        
        db.delete(service_card)
        db.commit()
        
        return {"success": True, "message": "Заведение успешно удалено"}
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: Ошибка при удалении заведения: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

@app.get("/api/v1/admin/test-media-server")
async def test_media_server(request: Request, db: Session = Depends(deps.get_db)):
    try:
        user = await check_admin_access(request, db)
        if isinstance(user, RedirectResponse):
            return JSONResponse(status_code=403, content={"success": False, "error": "Доступ запрещен"})
    except Exception as e:
        return JSONResponse(status_code=403, content={"success": False, "error": "Ошибка проверки доступа"})
    
    try:
        from app.utils.media_uploader import media_uploader
        ping_result = await media_uploader.ping_server()
        
        return {
            "success": True,
            "media_server_status": ping_result,
            "connection": ping_result.get("connected", False)
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": f"Ошибка тестирования медиа-сервера: {str(e)}"
        })

@app.post("/api/v1/admin/test-upload")
async def test_upload_endpoint(
    request: Request,
    photos: List[UploadFile] = File(...),
    db: Session = Depends(deps.get_db)
):
    try:
        user = await check_admin_access(request, db)
        if isinstance(user, RedirectResponse):
            return JSONResponse(status_code=403, content={"success": False, "error": "Доступ запрещен"})
    except Exception as e:
        return JSONResponse(status_code=403, content={"success": False, "error": "Ошибка проверки доступа"})
    
    try:
        result = {
            "success": True,
            "message": f"Получено {len(photos)} файлов для тестирования",
            "files_info": [],
            "media_server_test": None
        }
        
        for i, photo in enumerate(photos):
            file_info = {
                "index": i + 1,
                "filename": photo.filename,
                "content_type": photo.content_type,
                "size": photo.size if hasattr(photo, 'size') else "unknown"
            }
            result["files_info"].append(file_info)
        
        try:
            from app.utils.media_uploader import media_uploader
            ping_result = await media_uploader.ping_server()
            result["media_server_test"] = ping_result
        except Exception as e:
            result["media_server_test"] = {"error": str(e)}
        
        return result
        
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": f"Ошибка тестирования: {str(e)}"
        })

@app.post("/api/v1/admin/test-direct-upload")
async def test_direct_upload(
    request: Request,
    photos: List[UploadFile] = File(...),
    db: Session = Depends(deps.get_db)
):
    try:
        user = await check_admin_access(request, db)
        if isinstance(user, RedirectResponse):
            return JSONResponse(status_code=403, content={"success": False, "error": "Доступ запрещен"})
    except Exception as e:
        return JSONResponse(status_code=403, content={"success": False, "error": "Ошибка проверки доступа"})
    
    try:
        print(f"DEBUG: Прямой тест загрузки {len(photos)} файлов")
        
        files_data = []
        for i, file in enumerate(photos):
            file_content = await file.read()
            file_size = len(file_content)
            print(f"DEBUG: Файл {i+1}: {file.filename}, размер: {file_size} байт")
            
            files_data.append(
                ("images[]", (file.filename, file_content, file.content_type))
            )
            await file.seek(0)
        
        test_property_id = f"test-direct-{card_id if 'card_id' in locals() else 'unknown'}"
        
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"DEBUG: Отправляем на https://wazir.kg/state/upload.php")
            response = await client.post(
                "https://wazir.kg/state/upload.php",
                files=files_data,
                data={"property_id": test_property_id}
            )
            
            print(f"DEBUG: Статус ответа: {response.status_code}")
            print(f"DEBUG: Тело ответа: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "message": "Прямая загрузка успешна",
                    "server_response": result,
                    "files_sent": len(photos)
                }
            else:
                return JSONResponse(status_code=400, content={
                    "success": False,
                    "error": f"Ошибка медиа-сервера: {response.status_code}",
                    "response": response.text
                })
                
    except Exception as e:
        print(f"ERROR: Ошибка прямого теста: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": f"Ошибка теста: {str(e)}"
        })

@app.get("/api/v1/admin/test-simple")
async def test_simple():
    import time
    return {"status": "working", "message": "Сервер работает!", "timestamp": int(time.time())}

@app.post("/api/v1/admin/test-quick-upload")
async def test_quick_upload(photos: List[UploadFile] = File(...)):
    try:
        print(f"=== БЫСТРЫЙ ТЕСТ: {len(photos)} файлов ===")
        
        files_data = []
        for i, file in enumerate(photos):
            file_content = await file.read()
            print(f"Файл {i+1}: {file.filename}, размер: {len(file_content)}")
            files_data.append(("images[]", (file.filename, file_content, file.content_type)))
            await file.seek(0)
        
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("Отправляем на https://wazir.kg/state/upload.php")
            response = await client.post(
                "https://wazir.kg/state/upload.php",
                files=files_data,
                data={"property_id": "test-quick-123"}
            )
            
            print(f"Статус: {response.status_code}")
            print(f"Ответ: {response.text}")
            
            return {
                "status_code": response.status_code,
                "response": response.text,
                "files_sent": len(photos)
            }
            
    except Exception as e:
        print(f"ОШИБКА: {str(e)}")
        return {"error": str(e)}


async def check_company_access(request: Request, db: Session):
    auth_token = request.cookies.get('access_token')
    if not auth_token:
        return RedirectResponse('/companies/login', status_code=303)
    
    try:
        from jose import jwt
        payload = jwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        if not payload.get("is_company"):
            return RedirectResponse('/companies/login', status_code=303)
        
        user = db.query(models.User).filter(models.User.id == payload["sub"]).first()
        if not user or user.role != models.UserRole.COMPANY:
            return RedirectResponse('/companies/login', status_code=303)
        
        return user
        
    except Exception as e:
        print(f"DEBUG: Company auth error: {str(e)}")
        return RedirectResponse('/companies/login', status_code=303)

@app.get("/companies/login")
async def company_login_get(request: Request):
    return templates.TemplateResponse("companies/login.html", {"request": request})

@app.post("/companies/login")
async def company_login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    company = db.query(models.User).filter(
        models.User.email == email,
        models.User.role == models.UserRole.COMPANY
    ).first()
    
    if not company or not verify_password(password, company.hashed_password):
        return templates.TemplateResponse(
            "companies/login.html",
            {"request": request, "error": "Неверный email или пароль"}
        )
    
    access_token = create_access_token(
        data={"sub": str(company.id), "is_company": True}
    )
    
    response = RedirectResponse(url="/companies/dashboard", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False,
        max_age=3600 * 24,
        samesite="lax",
        path="/"
    )
    
    return response

@app.get("/companies/logout")
async def company_logout():
    response = RedirectResponse(url="/companies/login", status_code=303)
    response.delete_cookie("access_token")
    return response

@app.get("/companies", response_class=HTMLResponse)
@app.get("/companies/dashboard", response_class=HTMLResponse)
async def company_dashboard(request: Request, db: Session = Depends(deps.get_db)):
    user = await check_company_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    # Получаем статистику компании
    company_properties = db.query(models.Property).filter(
        models.Property.user_id == user.id
    ).all()
    
    stats = {
        "total_listings": len(company_properties),
        "active_listings": len([p for p in company_properties if p.status == models.PropertyStatus.ACTIVE]),
        "draft_listings": len([p for p in company_properties if p.status == models.PropertyStatus.DRAFT]),
        "views_this_month": sum([p.views_count for p in company_properties]) if hasattr(models.Property, 'views_count') else 0
    }
    
    return templates.TemplateResponse("companies/dashboard.html", {
        "request": request,
        "current_user": user,
        "stats": stats,
        "recent_properties": company_properties[:5]
    })

@app.get("/companies/listings", response_class=HTMLResponse)
async def company_listings(request: Request, db: Session = Depends(deps.get_db)):
    user = await check_company_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    properties = db.query(models.Property).filter(
        models.Property.user_id == user.id
    ).order_by(models.Property.created_at.desc()).all()
    
    return templates.TemplateResponse("companies/listings.html", {
        "request": request,
        "current_user": user,
        "properties": properties
    })

@app.get("/companies/create-listing", response_class=HTMLResponse)
async def company_create_listing(request: Request, db: Session = Depends(deps.get_db)):
    user = await check_company_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    categories = db.query(models.PropertyCategory).filter(
        models.PropertyCategory.is_active == True
    ).all() if hasattr(models, 'PropertyCategory') else []
    
    return templates.TemplateResponse("companies/create_listing.html", {
        "request": request,
        "current_user": user,
        "categories": categories
    })

@app.get("/companies/analytics", response_class=HTMLResponse)
async def company_analytics(request: Request, db: Session = Depends(deps.get_db)):
    user = await check_company_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    return templates.TemplateResponse("companies/analytics.html", {
        "request": request,
        "current_user": user
    })

@app.get("/companies/profile", response_class=HTMLResponse)
async def company_profile(request: Request, db: Session = Depends(deps.get_db)):
    user = await check_company_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    return templates.TemplateResponse("companies/profile.html", {
        "request": request,
        "current_user": user
    })

@app.get("/mobile/category/{category_slug}", response_class=HTMLResponse, name="category")
async def mobile_category(request: Request, category_slug: str, db: Session = Depends(deps.get_db)):
    categories = load_categories_from_json()
    
    category_name = None
    for cat in categories:
        if cat.get('slug') == category_slug:
            category_name = cat.get('name')
            break
    
    if category_name:
        return RedirectResponse(f'/mobile/search?category={category_name}', status_code=302)
    else:
        return RedirectResponse('/mobile/search', status_code=302)

@app.get("/mobile/search", response_class=HTMLResponse, name="search")
async def mobile_search(
    request: Request, 
    category: str = None, 
    price_min: int = None, 
    price_max: int = None, 
    min_area: float = None, 
    max_area: float = None,
    rooms: int = None,
    min_floor: int = None,
    max_floor: int = None,
    balcony: bool = None,
    furniture: bool = None,
    renovation: bool = None,
    parking: bool = None,
    q: str = None,
    db: Session = Depends(deps.get_db)
):
    print("\n===================================================")
    print("DEBUG: Параметры запроса:")
    print(f"  URL: {request.url}")
    print(f"  Поисковый запрос: {q}")
    print(f"  Категория: {category}")
    print(f"  Цена: {price_min} - {price_max}")
    print(f"  Площадь: {min_area} - {max_area}")
    print(f"  Комнаты: {rooms}")
    print(f"  Этаж: {min_floor} - {max_floor}")
    print(f"  Балкон: {balcony}, Мебель: {furniture}, Ремонт: {renovation}, Паркинг: {parking}")
    print("===================================================")
    
    if not category:
        category = "Недвижимость"
    
    query = db.query(models.Property).filter(models.Property.status == 'active')
    
    categories = db.query(models.Category).all()
    print(f"DEBUG: Загружены категории: {[cat.name for cat in categories]}")
    
    general_categories = load_categories_from_json()
    print(f"DEBUG: Загружены общие категории из JSON: {[cat['name'] for cat in general_categories]}")
    
    if category and category != "Недвижимость":
        print(f"DEBUG: Применяем фильтр по категории: {category}")
        query = query.join(models.Property.categories).filter(models.Category.name == category)
    
    if q:
        search_term = f"%{q}%"
        query = query.filter(or_(
            models.Property.title.ilike(search_term),
            models.Property.address.ilike(search_term),
            models.Property.description.ilike(search_term)
        ))
    
    if price_min is not None:
        query = query.filter(models.Property.price >= price_min)
    
    if price_max is not None:
        query = query.filter(models.Property.price <= price_max)
    
    if min_area is not None:
        query = query.filter(models.Property.area >= min_area)
    
    if max_area is not None:
        query = query.filter(models.Property.area <= max_area)
    
    if rooms is not None:
        query = query.filter(models.Property.rooms == rooms)
    
    if min_floor is not None:
        query = query.filter(models.Property.floor >= min_floor)
    
    if max_floor is not None:
        query = query.filter(models.Property.floor <= max_floor)
    
    if balcony is not None and balcony:
        query = query.filter(models.Property.has_balcony == True)
    
    if furniture is not None and furniture:
        query = query.filter(models.Property.has_furniture == True)
    
    if renovation is not None and renovation:
        query = query.filter(models.Property.has_renovation == True)
    
    if parking is not None and parking:
        query = query.filter(models.Property.has_parking == True)
    
    properties_db = query.options(joinedload(models.Property.images)).all()
    
    properties = []
    for prop in properties_db:
        main_image = next((img for img in prop.images if img.is_main), None) or \
                   (prop.images[0] if prop.images else None)
        
        images = [get_valid_image_url(img.url) for img in prop.images] if prop.images else []
        
        properties.append({
            "id": prop.id,
            "title": prop.title,
            "price": prop.price,
            "address": prop.address,
            "rooms": prop.rooms,
            "area": prop.area,
            "floor": prop.floor,
            "building_floors": prop.building_floors,
            "has_tour": bool(prop.tour_360_url or prop.tour_360_file_id),
            "tour_360_url": prop.tour_360_url,
            "tour_360_file_id": prop.tour_360_file_id,
            "tour_360_optimized_url": prop.tour_360_optimized_url,
            "has_balcony": prop.has_balcony,
            "has_furniture": prop.has_furniture,
            "has_renovation": prop.has_renovation,
            "has_parking": prop.has_parking,
            "image_url": get_valid_image_url(main_image.url if main_image else None),
            "images": images,
            "images_count": len(images)
        })
    
    weather = {"temperature": "+20°"}
    currency = {"value": "87.5"}
    
    return templates.TemplateResponse("layout/search.html", {
        "request": request, 
        "properties": properties,
        "weather": weather,
        "currency": currency,
        "categories": categories,
        "general_categories": general_categories,  # Добавляем общие категории
        "selected_category": category,
        "q": q,
        "filter": {
            "category": category,
            "price_min": price_min,
            "price_max": price_max,
            "min_area": min_area,
            "max_area": max_area,
            "rooms": rooms,
            "min_floor": min_floor,
            "max_floor": max_floor,
            "balcony": balcony,
            "furniture": furniture,
            "renovation": renovation,
            "parking": parking
        }
    })

@app.post("/api/v1/init-default-categories")
async def init_default_categories(request: Request, db: Session = Depends(deps.get_db)):
    try:
        from app.services.category import general_category
        general_category.create_default_categories(db)
        return {"message": "Категории по умолчанию созданы успешно"}
    except Exception as e:
        print(f"DEBUG: Ошибка создания категорий: {e}")
        return {"error": "Ошибка создания категорий"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
