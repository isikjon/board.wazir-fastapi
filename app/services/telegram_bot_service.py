import asyncio
import logging
from typing import Dict, Optional, Any
from contextlib import asynccontextmanager
from dataclasses import dataclass
import aiohttp
import random
import string
from datetime import datetime, timedelta

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import Conflict, Forbidden, BadRequest, TimedOut, NetworkError

from config import settings
from app.services.telegram_auth_service import telegram_auth_service

logger = logging.getLogger(__name__)

@dataclass
class SMSResult:
    success: bool
    message: str
    code: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class TelegramBotService:
    def __init__(self):
        self.application = None
        self.user_states: Dict[int, str] = {}
        self.is_running = False
        self.bot_task = None
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.bot_username = settings.TELEGRAM_BOT_USERNAME
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.codes_storage = {}  # Временное хранилище кодов (в продакшене использовать Redis)
        
    async def start_bot(self):
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.warning("TELEGRAM_BOT_TOKEN не настроен, бот не запущен")
            return
            
        if self.is_running:
            logger.warning("Бот уже запущен")
            return
            
        try:
            self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
            
            self.application.add_handler(CommandHandler("start", self._handle_start))
            self.application.add_handler(MessageHandler(filters.CONTACT, self._handle_contact))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
            
            await self.application.initialize()
            await self.application.start()
            
            try:
                await self.application.bot.delete_webhook(drop_pending_updates=True)
                logger.info("Webhook сброшен успешно")
            except Exception as e:
                logger.warning(f"Не удалось сбросить webhook: {e}")
            
            self.is_running = True
            logger.info("Telegram бот запущен успешно")
            
            self.bot_task = asyncio.create_task(self._run_polling())
            
        except Exception as e:
            logger.error(f"Ошибка запуска Telegram бота: {e}")
            self.is_running = False
            
    async def _run_polling(self):
        try:
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        except Conflict as e:
            logger.error(f"Конфликт Telegram бота (возможно, запущен другой экземпляр): {e}")
            self.is_running = False
        except (Forbidden, BadRequest) as e:
            logger.error(f"Ошибка авторизации/настройки Telegram бота: {e}")
            self.is_running = False
        except (TimedOut, NetworkError) as e:
            logger.warning(f"Сетевая ошибка Telegram бота (переподключение): {e}")
        except Exception as e:
            logger.error(f"Критическая ошибка в polling Telegram бота: {e}")
            self.is_running = False
            
    async def stop_bot(self):
        if not self.is_running or not self.application:
            return
            
        try:
            if self.bot_task:
                self.bot_task.cancel()
                try:
                    await self.bot_task
                except asyncio.CancelledError:
                    pass
                    
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            self.is_running = False
            logger.info("Telegram бот остановлен")
        except Exception as e:
            logger.error(f"Ошибка остановки Telegram бота: {e}")
    
    async def force_stop_webhook(self):
        try:
            if self.application and self.application.bot:
                await self.application.bot.delete_webhook(drop_pending_updates=True)
                logger.info("Webhook принудительно удален")
        except Exception as e:
            logger.error(f"Ошибка принудительного удаления webhook: {e}")
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        session_id = context.args[0] if context.args else None
        
        if session_id:
            self.user_states[user_id] = f"awaiting_phone:{session_id}"
            
            keyboard = [[KeyboardButton("📱 Поделиться номером", request_contact=True)]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            await update.message.reply_text(
                "Поделитесь номером телефона для подтверждения:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "Для авторизации перейдите на сайт и нажмите кнопку 'Авторизоваться через Telegram'"
            )

    async def _handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        
        if user_id not in self.user_states:
            await update.message.reply_text(
                "Начните с команды /start",
                reply_markup=ReplyKeyboardRemove()
            )
            return
        
        state = self.user_states[user_id]
        if not state.startswith("awaiting_phone:"):
            await update.message.reply_text(
                "Начните с команды /start",
                reply_markup=ReplyKeyboardRemove()
            )
            return
        
        session_id = state.split(":", 1)[1]
        contact = update.message.contact
        
        if contact.user_id != user_id:
            await update.message.reply_text(
                "Поделитесь своим номером телефона",
                reply_markup=ReplyKeyboardRemove()
            )
            return
        
        phone = contact.phone_number
        
        result = await telegram_auth_service.verify_phone_from_telegram(
            user_id, phone, session_id
        )
        
        if result.success:
            await update.message.reply_text(
                f"Код подтверждения отправлен! Введите его на сайте.",
                reply_markup=ReplyKeyboardRemove()
            )
            del self.user_states[user_id]
        else:
            await update.message.reply_text(
                f"Ошибка: {result.message}",
                reply_markup=ReplyKeyboardRemove()
            )
            del self.user_states[user_id]

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "Для авторизации используйте кнопку 'Поделиться номером'"
        )

    def generate_code(self) -> str:
        """Генерация 4-значного кода"""
        return ''.join(random.choices('0123456789', k=4))
    
    async def send_code_to_telegram(self, phone: str, chat_id: Optional[str] = None) -> SMSResult:
        """
        Отправка кода подтверждения в Telegram
        """
        try:
            # Генерируем код
            code = self.generate_code()
            
            # Сохраняем код с временной меткой
            self.codes_storage[phone] = {
                'code': code,
                'timestamp': datetime.now(),
                'chat_id': chat_id
            }
            
            # Если у нас есть chat_id, отправляем сообщение напрямую
            if chat_id:
                message = f"🔐 Ваш код подтверждения: {code}\n\nКод действителен 5 минут."
                
                url = f"{self.base_url}/sendMessage"
                payload = {
                    'chat_id': chat_id,
                    'text': message,
                    'parse_mode': 'HTML'
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload) as response:
                        if response.status == 200:
                            return SMSResult(
                                success=True,
                                message=f"SMS код отправлен в Telegram: {code}",
                                code=code,
                                data={'chat_id': chat_id}
                            )
                        else:
                            logger.error(f"Ошибка отправки в Telegram: {response.status}")
                            return SMSResult(
                                success=False,
                                message="Ошибка отправки в Telegram"
                            )
            else:
                # Если нет chat_id, возвращаем код для отображения (для тестирования)
                return SMSResult(
                    success=True,
                    message=f"SMS код сгенерирован: {code}",
                    code=code,
                    data={'phone': phone}
                )
                
        except Exception as e:
            logger.error(f"Ошибка при отправке кода в Telegram: {str(e)}")
            return SMSResult(
                success=False,
                message=f"Ошибка отправки: {str(e)}"
            )
    
    def verify_code(self, phone: str, code: str) -> bool:
        """
        Проверка кода подтверждения
        """
        if phone not in self.codes_storage:
            return False
        
        stored_data = self.codes_storage[phone]
        
        # Проверяем, не истек ли код (5 минут)
        if datetime.now() - stored_data['timestamp'] > timedelta(minutes=5):
            del self.codes_storage[phone]
            return False
        
        # Проверяем код
        if stored_data['code'] == code:
            # Удаляем код после успешной проверки
            del self.codes_storage[phone]
            return True
        
        return False
    
    async def get_bot_info(self) -> Dict[str, Any]:
        """
        Получение информации о боте
        """
        try:
            url = f"{self.base_url}/getMe"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}

# Создаем глобальный экземпляр сервиса
telegram_bot_service = TelegramBotService() 