from sqlalchemy import Boolean, Column, String, Integer, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from database import Base
from .base import TimestampMixin
import enum


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    USER = "USER"
    MANAGER = "MANAGER"
    COMPANY = "COMPANY"  # Юридическое лицо


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(20), unique=True, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    role = Column(Enum(UserRole), default=UserRole.USER)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING)
    
    # Поля для юридических лиц
    company_name = Column(String(255), nullable=True)  # Название компании
    company_number = Column(String(100), nullable=True)  # Номер юр.лица (ИНН/ОГРН)
    company_owner = Column(String(255), nullable=True)  # На кого оформлено
    company_logo_url = Column(String(500), nullable=True)  # URL логотипа
    company_description = Column(Text, nullable=True)  # Описание компании
    company_address = Column(String(500), nullable=True)  # Адрес компании
    
    properties = relationship("Property", back_populates="owner")
    favorites = relationship("Favorite", back_populates="user")
    # Отношения messages_sent и messages_received будут определены через backref в Message
    # support_tickets будет определено через backref в SupportTicket 
    support_tickets = relationship("SupportTicket", back_populates="user")
    
    def check_password(self, password: str) -> bool:
        """Проверяет пароль пользователя"""
        from app.utils.security import verify_password
        return verify_password(password, self.hashed_password) 