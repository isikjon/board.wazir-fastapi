from .user import user
from .property import property, CRUDCategory
from .message import message
from .request import request
from app.models.property import Category

try:
    from .telegram_auth_service import telegram_auth_service
    from .telegram_bot_service import telegram_bot_service
except ImportError:
    telegram_auth_service = None
    telegram_bot_service = None

# Создаем экземпляр CRUDCategory и экспортируем его
category = CRUDCategory(Category) 