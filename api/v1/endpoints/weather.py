from typing import Any, Dict

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
def get_weather(
    request: Request
) -> Any:
    """
    Получить данные о погоде.
    """
    # В реальном приложении здесь был бы API-запрос к сервису погоды
    # Возвращаем тестовые данные, независимо от авторизации
    return {"temperature": "+20°"}
