from typing import Any, Dict

from fastapi import APIRouter, Depends, Request, Header
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param

from app.api import deps
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=Dict[str, str])
def get_currency(
    request: Request,
    authorization: str = Header(None),
) -> Any:
    """
    Получить данные о курсе валюты.
    """
    # В реальном приложении здесь был бы API-запрос к сервису валют
    return {"value": "69.8"}
