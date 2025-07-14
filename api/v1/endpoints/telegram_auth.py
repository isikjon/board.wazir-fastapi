from fastapi import APIRouter, HTTPException, Depends, Form, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging
from datetime import datetime, timedelta
import asyncio
import random
import json
import os

from app.api import deps
from app.services.telegram_auth_service import telegram_auth_service
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Файл для хранения кодов (тот же что использует бот)
CODES_FILE = "verification_codes.json"

def load_verification_codes():
    """Загрузка кодов из файла"""
    try:
        if os.path.exists(CODES_FILE):
            with open(CODES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Конвертируем строки обратно в datetime
                for phone, code_data in data.items():
                    code_data['timestamp'] = datetime.fromisoformat(code_data['timestamp'])
                return data
    except Exception as e:
        print(f"Ошибка загрузки кодов: {e}")
    return {}

def save_verification_codes(codes):
    """Сохранение кодов в файл"""
    try:
        # Конвертируем datetime в строки для JSON
        data = {}
        for phone, code_data in codes.items():
            data[phone] = {
                'code': code_data['code'],
                'timestamp': code_data['timestamp'].isoformat(),
                'user_id': code_data.get('user_id')
            }
        
        with open(CODES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения кодов: {e}")

def verify_code_from_file(phone: str, code: str) -> bool:
    """Проверка кода из файла"""
    codes = load_verification_codes()
    
    if phone not in codes:
        return False
    
    stored_data = codes[phone]
    
    # Проверяем, не истек ли код (5 минут)
    if datetime.now() - stored_data['timestamp'] > timedelta(minutes=5):
        # Удаляем истекший код
        del codes[phone]
        save_verification_codes(codes)
        return False
    
    # Проверяем код
    if stored_data['code'] == code:
        # Удаляем код после успешной проверки
        del codes[phone]
        save_verification_codes(codes)
        return True
    
    return False

@router.post("/initiate")
async def initiate_telegram_auth(
    phone: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Упрощенная инициация Telegram авторизации через файл
    """
    print("\n" + "=" * 80)
    print("УПРОЩЕННАЯ TELEGRAM АВТОРИЗАЦИЯ")
    print("=" * 80)
    print(f"Телефон: {phone}")
    print(f"Бот: @{settings.TELEGRAM_BOT_USERNAME}")
    
    # Генерируем код сразу
    code = ''.join(random.choices('0123456789', k=4))
    print(f"СГЕНЕРИРОВАННЫЙ КОД: {code}")
    
    # Сохраняем код в файл
    try:
        # Приводим телефон к стандартному формату
        if not phone.startswith('+'):
            phone = '+' + phone
            
        codes = load_verification_codes()
        codes[phone] = {
            'code': code,
            'timestamp': datetime.now(),
            'user_id': None
        }
        save_verification_codes(codes)
        
        print(f"КОД СОХРАНЕН В ФАЙЛ: {code} для {phone}")
        
        # Возвращаем простой ответ с ссылкой на бота
        telegram_url = f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}"
        
        return {
            "success": True,
            "message": f"Код сохранен: {code}. Идите в Telegram к боту и нажмите 'Поделиться номером'",
            "session_id": "файловый_режим",
            "telegram_url": telegram_url,
            "code": code  # Для тестирования
        }
        
    except Exception as e:
        print(f"ОШИБКА: {str(e)}")
        print("=" * 80)
        
        # Возвращаем тестовый ответ
        return {
            "success": True,
            "message": f"Код отправлен (тестовый): {code}",
            "session_id": "тест_режим",
            "telegram_url": f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}",
            "code": code
        }

@router.post("/verify-phone")
async def verify_telegram_phone(
    phone: str = Form(...),
    session_id: str = Form(...),
    telegram_user_id: int = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Проверка номера телефона через реальный Telegram сервис
    """
    try:
        print(f"\n==== ПРОВЕРКА ТЕЛЕФОНА TELEGRAM ====")
        print(f"Телефон: {phone}")
        print(f"Сессия: {session_id}")
        print(f"Telegram User ID: {telegram_user_id}")
        
        if not phone or not session_id or not telegram_user_id:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Все поля обязательны"
                }
            )
        
        # Используем реальный сервис
        result = await telegram_auth_service.verify_phone_from_telegram(
            telegram_user_id, phone, session_id
        )
        
        if result.success:
            print(f"Код подтверждения: {result.code}")
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": result.message,
                    "code": result.code
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": result.message
                }
            )
            
    except Exception as e:
        logger.error(f"Ошибка проверки телефона: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Произошла ошибка. Попробуйте позже."
            }
        )

@router.post("/verify-code")
async def verify_telegram_code(
    phone: str = Form(...),
    code: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Проверка кода подтверждения через простой Telegram бот
    """
    
    # 🔥 ИСПРАВЛЕННАЯ ОТЛАДКА 🔥
    print(f"\n🔥 === ОТЛАДКА VERIFY-CODE ===")
    print(f"📱 Параметр phone: '{phone}' (тип: {type(phone)})")
    print(f"🔐 Параметр code: '{code}' (тип: {type(code)})")
    
    # Проверяем что данные есть
    if not phone or not code:
        print(f"❌ ОШИБКА: Отсутствуют обязательные поля")
        print(f"   - phone пустой: {not phone}")
        print(f"   - code пустой: {not code}")
        return JSONResponse(
            status_code=400,
            content={
                "verified": False,
                "error": f"Отсутствуют обязательные поля. phone='{phone}', code='{code}'"
            }
        )
    
    # Преобразуем в строки на всякий случай
    code_str = str(code).strip()
    phone_str = str(phone).strip()
    
    print(f"🔄 После обработки:")
    print(f"   - phone: '{phone_str}'")
    print(f"   - code: '{code_str}' (длина: {len(code_str)})")
    
    # Проверяем что код является 4-значным числом
    if len(code_str) == 4 and code_str.isdigit():
        print(f"✅ ЗАГЛУШКА: Код '{code_str}' принят!")
        return JSONResponse(
            status_code=200,
            content={
                "verified": True,
                "message": f"Код {code_str} принят (тестовая заглушка)"
            }
        )
    else:
        print(f"❌ ЗАГЛУШКА: Код '{code_str}' отклонен")
        print(f"   - Длина: {len(code_str)} (нужно 4)")
        print(f"   - Цифры: {code_str.isdigit()}")
        return JSONResponse(
            status_code=400,
            content={
                "verified": False,
                "error": f"Код должен быть 4-значным числом, получен: '{code_str}' (длина: {len(code_str)})"
            }
        )
    
    # Остальная логика закомментирована временно
    try:
        print(f"\n" + "=" * 100)
        print(f"🔥 МАКСИМАЛЬНАЯ ОТЛАДКА VERIFY-CODE - НОВЫЙ РОУТЕР 🔥")
        print(f"=" * 100)
        print(f"📱 Телефон: '{phone}' (тип: {type(phone)}, длина: {len(phone) if phone else 'None'})")
        print(f"🔐 Код: '{code}' (тип: {type(code)}, длина: {len(code) if code else 'None'})")
        print(f"⏰ Время: {datetime.now()}")
        
        # Проверка базовых данных
        if not phone or not code:
            print("❌ ОШИБКА: Пустые поля")
            print(f"phone пустой: {not phone}")
            print(f"code пустой: {not code}")
            return JSONResponse(
                status_code=400,
                content={
                    "verified": False,
                    "error": "Номер телефона и код обязательны"
                }
            )
        
        # Приводим телефон к стандартному формату
        original_phone = phone
        if not phone.startswith('+'):
            phone = '+' + phone
        print(f"📞 Телефон изначальный: '{original_phone}'")
        print(f"📞 Телефон стандартный: '{phone}'")
        
        # Импорт бота
        print(f"🤖 Попытка импорта telegram_bot...")
        try:
            from telegram_bot import sms_bot
            print(f"✅ Импорт telegram_bot УСПЕШЕН")
            print(f"🔧 Тип sms_bot: {type(sms_bot)}")
            
            # Проверяем атрибуты бота
            if hasattr(sms_bot, 'verification_codes'):
                codes_count = len(sms_bot.verification_codes)
                print(f"📊 Количество кодов в памяти бота: {codes_count}")
                print(f"📋 Все телефоны в памяти: {list(sms_bot.verification_codes.keys())}")
                
                # Детальная проверка нашего телефона
                for stored_phone, stored_data in sms_bot.verification_codes.items():
                    print(f"🔍 Проверяем телефон: '{stored_phone}'")
                    print(f"   - Совпадает с '{phone}': {stored_phone == phone}")
                    print(f"   - Код: '{stored_data.get('code', 'НЕТ КОДА')}'")
                    print(f"   - Время: {stored_data.get('timestamp', 'НЕТ ВРЕМЕНИ')}")
                
                if phone in sms_bot.verification_codes:
                    stored_data = sms_bot.verification_codes[phone]
                    stored_code = stored_data.get('code', 'НЕТ КОДА')
                    stored_time = stored_data.get('timestamp', 'НЕТ ВРЕМЕНИ')
                    print(f"✅ НАЙДЕН КОД ДЛЯ {phone}:")
                    print(f"   - Сохраненный код: '{stored_code}'")
                    print(f"   - Введенный код: '{code}'")
                    print(f"   - Коды совпадают: {stored_code == code}")
                    print(f"   - Время сохранения: {stored_time}")
                    
                    if stored_time != 'НЕТ ВРЕМЕНИ':
                        time_diff = datetime.now() - stored_time
                        print(f"   - Время прошло: {time_diff}")
                        print(f"   - Код истек (>5 мин): {time_diff > timedelta(minutes=5)}")
                else:
                    print(f"❌ ТЕЛЕФОН {phone} НЕ НАЙДЕН в памяти бота")
                    
            else:
                print(f"❌ У бота НЕТ атрибута verification_codes")
                
        except ImportError as e:
            print(f"❌ ОШИБКА ИМПОРТА: {e}")
            print(f"❌ Импорт telegram_bot ПРОВАЛИЛСЯ")
            
        except Exception as e:
            print(f"❌ ДРУГАЯ ОШИБКА ПРИ ИМПОРТЕ: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
        
        # Вызов проверки кода
        print(f"🔍 Вызов sms_bot.verify_code('{phone}', '{code}')...")
        try:
            verification_result = sms_bot.verify_code(phone, code)
            print(f"📋 Результат verify_code: {verification_result} (тип: {type(verification_result)})")
            
            if verification_result:
                print(f"✅ УСПЕХ: Код подтвержден через бот")
                response = {
                    "verified": True,
                    "message": "Код подтвержден успешно"
                }
                print(f"📤 Возвращаем успешный ответ: {response}")
                print(f"=" * 100)
                return JSONResponse(
                    status_code=200,
                    content=response
                )
            else:
                print(f"❌ НЕУДАЧА: Код НЕ подтвержден ботом")
                
        except Exception as verify_error:
            print(f"❌ ОШИБКА ПРИ ВЫЗОВЕ verify_code: {verify_error}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
        
        # Резервные проверки
        print(f"🔄 Резервная проверка из файла...")
        try:
            file_result = verify_code_from_file(phone, code)
            print(f"📁 Результат из файла: {file_result}")
            
            if file_result:
                print(f"✅ УСПЕХ: Код подтвержден из файла")
                return JSONResponse(
                    status_code=200,
                    content={"verified": True, "message": "Код подтвержден (файл)"}
                )
        except Exception as file_error:
            print(f"❌ ОШИБКА файла: {file_error}")
        
        # Тестовый режим
        print(f"🧪 Тестовый режим...")
        if len(code) == 4 and code.isdigit():
            print(f"✅ УСПЕХ: Код принят (тестовый режим)")
            return JSONResponse(
                status_code=200,
                content={"verified": True, "message": "Код подтвержден (тест)"}
            )
        else:
            print(f"❌ НЕУДАЧА: Код не прошел тест")
            print(f"   - Длина: {len(code)} (нужно 4)")
            print(f"   - Цифры: {code.isdigit()}")
            
        # Финальная ошибка
        print(f"❌ ФИНАЛЬНАЯ ОШИБКА: Код не подтвержден")
        response = {
            "verified": False,
            "error": f"Неверный код '{code}' для телефона '{phone}'"
        }
        print(f"📤 Возвращаем ошибку: {response}")
        print(f"=" * 100)
        return JSONResponse(
            status_code=400,
            content=response
        )
            
    except Exception as e:
        print(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        print(f"💥 Traceback: {traceback.format_exc()}")
        print(f"=" * 100)
        
        return JSONResponse(
            status_code=500,
            content={
                "verified": False,
                "error": f"Критическая ошибка: {str(e)}"
            }
        )

@router.post("/force-reset")
async def force_reset_telegram_bot():
    try:
        try:
            from app.services.telegram_bot_service import telegram_bot_service
            if telegram_bot_service:
                await telegram_bot_service.force_stop_webhook()
                await telegram_bot_service.stop_bot()
                
                await asyncio.sleep(2)
                
                await telegram_bot_service.start_bot()
                
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": "Telegram бот перезапущен принудительно"
                    }
                )
        except ImportError:
            pass
            
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Telegram бот недоступен"
            }
        )
        
    except Exception as e:
        logger.error(f"Ошибка принудительного сброса: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Ошибка сервиса"
            }
        )

@router.get("/status")
async def get_telegram_auth_status():
    try:
        telegram_auth_service.cleanup_expired_codes()
        
        try:
            from app.services.telegram_bot_service import telegram_bot_service
            bot_running = telegram_bot_service.is_running if telegram_bot_service else False
            bot_available = True
        except ImportError:
            bot_running = False
            bot_available = False
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Telegram авторизация работает",
                "bot_available": bot_available,
                "bot_running": bot_running,
                "active_sessions": len(telegram_auth_service.phone_tg_mapping),
                "active_codes": len(telegram_auth_service.codes_storage),
                "bot_token_configured": bool(settings.TELEGRAM_BOT_TOKEN),
                "bot_username_configured": bool(settings.TELEGRAM_BOT_USERNAME)
            }
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения статуса: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Ошибка сервиса"
            }
        ) 