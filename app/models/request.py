from sqlalchemy import Column, String, Integer, Boolean, Float, ForeignKey, Text, Enum, DateTime
from sqlalchemy.orm import relationship
from database import Base
from .base import TimestampMixin
import enum


class RequestStatus(str, enum.Enum):
    NEW = "new"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"


class RequestType(str, enum.Enum):
    VIEWING = "viewing"  # Просмотр объекта
    PURCHASE = "purchase"  # Покупка объекта
    SELL = "sell"  # Продажа объекта
    CONSULTATION = "consultation"  # Консультация
    OTHER = "other"  # Другое


class Request(Base, TimestampMixin):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    description = Column(Text, nullable=True)
    type = Column(Enum(RequestType), default=RequestType.OTHER)
    status = Column(Enum(RequestStatus), default=RequestStatus.NEW)
    appointment_date = Column(DateTime, nullable=True)  # Дата встречи/консультации
    
    # Связь с пользователем, создавшим заявку
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", backref="requests")
    
    # Связь с объектом недвижимости (если заявка связана с объектом)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)
    property = relationship("Property", backref="requests")
    
    # Дополнительные поля
    contact_phone = Column(String(20), nullable=True)  # Контактный телефон
    contact_email = Column(String(255), nullable=True)  # Контактный email
    notes = Column(Text, nullable=True)  # Дополнительные примечания
    is_urgent = Column(Boolean, default=False)  # Срочная заявка 