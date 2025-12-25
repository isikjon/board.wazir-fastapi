from datetime import datetime, timedelta
from typing import Any, Union, Optional
import bcrypt

from jose import jwt
from config import settings

ALGORITHM = settings.ALGORITHM


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль используя bcrypt"""
    try:
        # Проверяем что хеш начинается с $2b$ (bcrypt формат)
        if not hashed_password.startswith('$2b$'):
            # Если старый формат от passlib, конвертируем
            if hashed_password.startswith('$2a$') or hashed_password.startswith('$2y$'):
                # Используем bcrypt напрямую
                password_bytes = plain_password.encode('utf-8')
                if len(password_bytes) > 72:
                    password_bytes = password_bytes[:72]
                return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
            return False
        
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
    except Exception as e:
        return False


def get_password_hash(password: str) -> str:
    """Хеширует пароль используя bcrypt"""
    # Bcrypt ограничение: пароль не может быть длиннее 72 байт
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Генерируем соль и хешируем
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8') 