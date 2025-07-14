from typing import Any, Dict

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
def get_currency(
    request: Request
) -> Any:
    """
    Получить данные о курсе валюты.
    """
    # В реальном приложении здесь был бы API-запрос к сервису валют
    # Возвращаем тестовые данные, независимо от авторизации
    return {"value": "69.8"}
