from typing import Generator, Optional
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from datetime import datetime

from database import SessionLocal
from config import settings
from app import models

def get_db() -> Generator:
    """Получение сессии базы данных"""
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[models.User]:
    """Получение текущего пользователя (опционально)"""
    # Пытаемся получить токен из заголовка Authorization
    auth_header = request.headers.get('Authorization')
    token = None
    
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
    else:
        # Если токена в заголовке нет, пытаемся получить из cookies
        token = request.cookies.get('access_token')
    
    if not token:
        return None
    
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            return None
            
        # Проверяем срок действия токена
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            print(f"DEBUG: Token expired for user {user_id}")
            return None
            
    except JWTError as e:
        print(f"DEBUG: JWT decode error: {e}")
        return None
    except Exception as e:
        print(f"DEBUG: Unexpected error during token decode: {e}")
        return None
    
    # Получаем пользователя из базы данных
    try:
        user = db.query(models.User).filter(models.User.id == int(user_id)).first()
        if not user:
            print(f"DEBUG: User with id {user_id} not found in database")
            return None
        return user
    except Exception as e:
        print(f"DEBUG: Database error when fetching user {user_id}: {e}")
        return None

def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> models.User:
    """Получение текущего пользователя (обязательно)"""
    current_user = get_current_user_optional(request, db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return current_user

def get_current_active_user(
    request: Request,
    db: Session = Depends(get_db)
) -> models.User:
    """Получение активного пользователя"""
    try:
        current_user = get_current_user(request, db)
        
        # Проверяем, что current_user является объектом User, а не словарем
        if isinstance(current_user, dict):
            print(f"DEBUG: current_user is dict instead of User object: {current_user}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user object format"
            )
            
        if not hasattr(current_user, 'is_active'):
            print(f"DEBUG: current_user object missing is_active attribute: {type(current_user)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user object structure"
            )
            
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
            
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Unexpected error in get_current_active_user: {e}")
        print(f"DEBUG: Error type: {type(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}"
        )

def get_current_active_admin(
    request: Request,
    db: Session = Depends(get_db)
) -> models.User:
    current_user = get_current_active_user(request, db)
    if current_user.role.value != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав"
        )
    return current_user 