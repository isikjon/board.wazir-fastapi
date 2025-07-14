from pydantic_settings import BaseSettings
from pathlib import Path
import os
from typing import Optional, List, Union
from pydantic import validator


class Settings(BaseSettings):
    # Base
    BASE_DIR: Path = Path(__file__).resolve().parent
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    PROJECT_NAME: str = "Wazir Недвижимость"

    # Database
    DATABASE_URL: str
    
    # JWT Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Google Maps API
    GOOGLE_MAPS: str
    
    # Media
    MEDIA_DIR: str = "media"
    
    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = ["*"]

    # Email
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: Optional[str] = None
    MAIL_PORT: Optional[int] = 587
    MAIL_SERVER: Optional[str] = None
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False
    
    # Devino SMS Settings
    DEVINO_API_URL: str = "https://phoneverification.devinotele.com"
    DEVINO_API_KEY: Optional[str] = None  # Получается из переменной окружения DEVINO_API_KEY
    DEVINO_TIMEOUT: int = 30
    
    # SMS Debug Settings
    DEBUG_SMS: bool = True
    SMS_CODE_EXPIRY_MINUTES: int = 5
    SMS_RESEND_COOLDOWN_SECONDS: int = 60
    
    # Telegram Auth Settings
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_BOT_USERNAME: Optional[str] = None
    TELEGRAM_CODE_EXPIRY_MINUTES: int = 5
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings() 