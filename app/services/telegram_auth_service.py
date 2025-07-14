"""
Сервис для авторизации через Telegram
Управление сессиями, проверка номеров телефонов и генерация кодов
"""

import asyncio
import json
import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Union, Any, List
from dataclasses import dataclass

import httpx
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TelegramAuthResponse:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None

# Результаты операций
class TelegramAuthResult:
    def __init__(self, success: bool, session_id: str = None, code: str = None, message: str = None):
        self.success = success
        self.session_id = session_id
        self.code = code
        self.message = message

class TelegramAuthService:
    """Сервис для авторизации через Telegram"""
    
    def __init__(self):
        self.bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        self.bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', None)
        self.codes_storage = {}
        self.phone_tg_mapping = {}
        self.code_expiry = 300
        
        # Хранение сессий в памяти (в реальном приложении лучше использовать Redis)
        self.sessions: Dict[str, Dict[str, Any]] = {}
        # Срок действия сессии в минутах
        self.session_lifetime = 15
        
        logger.info("🚀 Инициализация TelegramAuthService")
        
    def generate_code(self) -> str:
        return str(random.randint(1000, 9999))
    
    async def create_session(self, phone: str) -> TelegramAuthResult:
        """
        Создает новую сессию авторизации и возвращает session_id
        """
        # Генерируем уникальный session_id
        session_id = str(uuid.uuid4())
        
        # Нормализуем телефон (удаляем все кроме цифр)
        normalized_phone = ''.join(filter(str.isdigit, phone))
        
        # Создаем сессию
        self.sessions[session_id] = {
            'phone': normalized_phone,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(minutes=self.session_lifetime),
            'confirmed': False,
            'telegram_user_id': None,
            'code': None
        }
        
        # Формируем ссылку на Telegram бота
        telegram_url = f"https://t.me/{self.bot_username}?start={session_id}"
        
        logger.info(f"✅ Создана сессия: {session_id} для телефона {normalized_phone}")
        logger.info(f"🔗 Telegram URL: {telegram_url}")
        
        return TelegramAuthResult(
            success=True,
            session_id=session_id,
            message="Сессия создана успешно"
        )
    
    async def verify_phone_from_telegram(self, telegram_user_id: int, phone: str, session_id: str) -> TelegramAuthResult:
        """
        Проверяет телефон полученный от Telegram и сравнивает с указанным при инициализации
        Если совпадает - генерирует код и привязывает его к сессии
        """
        # Проверяем существование сессии
        if session_id not in self.sessions:
            logger.warning(f"❌ Сессия не найдена: {session_id}")
            return TelegramAuthResult(
                success=False,
                message="Сессия не найдена или истекла"
            )
        
        session = self.sessions[session_id]
        
        # Проверяем срок действия сессии
        if datetime.now() > session['expires_at']:
            logger.warning(f"⌛ Сессия истекла: {session_id}")
            del self.sessions[session_id]
            return TelegramAuthResult(
                success=False,
                message="Сессия истекла"
            )
        
        # Нормализуем телефоны для сравнения (только цифры)
        session_phone = ''.join(filter(str.isdigit, session['phone']))
        telegram_phone = ''.join(filter(str.isdigit, phone))
        
        logger.info(f"📱 Сравнение телефонов:")
        logger.info(f"   - Сессия:   {session_phone}")
        logger.info(f"   - Telegram: {telegram_phone}")
        
        # Проверяем соответствие телефонов
        if session_phone != telegram_phone:
            logger.warning(f"❌ Телефоны не совпадают: {session_phone} != {telegram_phone}")
            return TelegramAuthResult(
                success=False,
                message="Номер телефона не совпадает с указанным при инициализации"
            )
        
        # Генерируем 4-значный код
        code = ''.join(random.choices('0123456789', k=4))
        
        # Обновляем сессию
        session['confirmed'] = True
        session['telegram_user_id'] = telegram_user_id
        session['code'] = code
        
        logger.info(f"✅ Телефон подтвержден для сессии {session_id}")
        logger.info(f"🔢 Сгенерирован код: {code}")
        
        return TelegramAuthResult(
            success=True,
            code=code,
            message="Телефон подтвержден, код отправлен"
        )
    
    async def verify_code(self, phone: str, code: str) -> TelegramAuthResult:
        """
        Проверяет код авторизации
        """
        # Нормализуем телефон
        normalized_phone = ''.join(filter(str.isdigit, phone))
        
        # Ищем сессию по телефону
        session_id = None
        for sid, session in self.sessions.items():
            session_phone = ''.join(filter(str.isdigit, session['phone']))
            if session_phone == normalized_phone and session['confirmed']:
                session_id = sid
                break
        
        if not session_id:
            logger.warning(f"❌ Сессия не найдена для телефона: {normalized_phone}")
            return TelegramAuthResult(
                success=False,
                message="Сессия не найдена или телефон не подтвержден"
            )
        
        session = self.sessions[session_id]
        
        # Проверяем срок действия сессии
        if datetime.now() > session['expires_at']:
            logger.warning(f"⌛ Сессия истекла: {session_id}")
            del self.sessions[session_id]
            return TelegramAuthResult(
                success=False,
                message="Сессия истекла"
            )
        
        # Проверяем код
        if session['code'] != code:
            logger.warning(f"❌ Неверный код: {code} != {session['code']}")
            return TelegramAuthResult(
                success=False,
                message="Неверный код"
            )
        
        logger.info(f"✅ Код подтвержден для сессии {session_id}")
        
        # Удаляем сессию после успешной авторизации
        del self.sessions[session_id]
        
        return TelegramAuthResult(
            success=True,
            message="Код подтвержден"
        )
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Возвращает статус сессии
        """
        if session_id not in self.sessions:
            return {
                "found": False,
                "message": "Сессия не найдена"
            }
        
        session = self.sessions[session_id]
        
        # Проверяем срок действия сессии
        if datetime.now() > session['expires_at']:
            del self.sessions[session_id]
            return {
                "found": False,
                "message": "Сессия истекла"
            }
        
        return {
            "found": True,
            "confirmed": session['confirmed'],
            "expires_in": int((session['expires_at'] - datetime.now()).total_seconds()),
            "phone": session['phone'][-4:].rjust(len(session['phone']), '*')  # Маскируем номер
        }
    
    def cleanup_expired_sessions(self) -> int:
        """
        Удаляет истекшие сессии
        Возвращает количество удаленных сессий
        """
        expired_count = 0
        current_time = datetime.now()
        
        # Создаем список ключей для удаления
        to_delete = []
        for session_id, session in self.sessions.items():
            if current_time > session['expires_at']:
                to_delete.append(session_id)
        
        # Удаляем истекшие сессии
        for session_id in to_delete:
            del self.sessions[session_id]
            expired_count += 1
        
        if expired_count > 0:
            logger.info(f"🧹 Удалено {expired_count} истекших сессий")
        
        return expired_count
    
    async def _send_code_to_telegram(self, telegram_id: int, code: str):
        if not self.bot_token:
            logger.warning("Telegram bot token не настроен")
            return
            
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                    json={
                        'chat_id': telegram_id,
                        'text': f"Код подтверждения: {code}",
                        'parse_mode': 'HTML'
                    }
                )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения в Telegram: {e}")
    
    def _normalize_phone(self, phone: str) -> str:
        phone = phone.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if phone.startswith('+'):
            phone = phone[1:]
        elif phone.startswith('8') and len(phone) == 11:
            phone = '7' + phone[1:]
        return phone
    
    def cleanup_expired_codes(self):
        now = datetime.now()
        expired_phones = []
        
        for phone, data in self.codes_storage.items():
            if now - data['created_at'] > timedelta(seconds=self.code_expiry):
                expired_phones.append(phone)
        
        for phone in expired_phones:
            del self.codes_storage[phone]
            
        expired_sessions = []
        for phone, data in self.phone_tg_mapping.items():
            if now - data['created_at'] > timedelta(minutes=5):
                expired_sessions.append(phone)
                
        for phone in expired_sessions:
            del self.phone_tg_mapping[phone]

    async def initiate_auth(self, phone: str) -> TelegramAuthResponse:
        """
        Инициализация авторизации через Telegram
        Создает сессию и возвращает URL для перехода в Telegram
        """
        try:
            # Создаем сессию
            result = await self.create_session(phone)
            
            if result.success:
                # Формируем URL для Telegram
                if not self.bot_username:
                    logger.error("TELEGRAM_BOT_USERNAME не настроен")
                    return TelegramAuthResponse(
                        success=False,
                        message="Telegram бот не настроен",
                        error_code="BOT_NOT_CONFIGURED"
                    )
                
                telegram_url = f"https://t.me/{self.bot_username}?start={result.session_id}"
                
                return TelegramAuthResponse(
                    success=True,
                    message=result.message,
                    data={
                        "session_id": result.session_id,
                        "telegram_url": telegram_url
                    }
                )
            else:
                return TelegramAuthResponse(
                    success=False,
                    message=result.message,
                    error_code="SESSION_CREATION_FAILED"
                )
                
        except Exception as e:
            logger.error(f"Ошибка инициализации авторизации: {e}")
            return TelegramAuthResponse(
                success=False,
                message="Произошла ошибка при создании сессии",
                error_code="INTERNAL_ERROR"
            )

# Глобальный экземпляр сервиса
telegram_auth_service = TelegramAuthService() 