from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
import re

from app.models.user import UserRole, UserStatus


class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    role: Optional[UserRole] = UserRole.USER
    status: Optional[UserStatus] = UserStatus.PENDING
    
    @validator('phone')
    def validate_phone(cls, v):
        if v is None:
            return v
        pattern = r'^\+[1-9]\d{1,14}$'
        if not re.match(pattern, v):
            raise ValueError('Телефон должен быть в формате +xxxxxxxxxxx')
        return v


class UserCreate(UserBase):
    email: EmailStr
    phone: str
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        return v


class UserUpdate(UserBase):
    password: Optional[str] = None


class UserInDBBase(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserInDB(UserInDBBase):
    hashed_password: str


class User(UserInDBBase):
    pass 