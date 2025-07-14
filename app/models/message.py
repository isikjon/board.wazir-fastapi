from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from database import Base
from .base import TimestampMixin
import enum


class MessageStatus(str, enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    status = Column(Enum(MessageStatus), default=MessageStatus.SENT)
    
    sender_id = Column(Integer, ForeignKey("users.id"))
    recipient_id = Column(Integer, ForeignKey("users.id"))
    
    sender = relationship("User", foreign_keys=[sender_id], backref="messages_sent")
    recipient = relationship("User", foreign_keys=[recipient_id], backref="messages_received")


# Удалены дублирующие классы тикетов:
# class TicketStatus(str, enum.Enum): ...
# class SupportTicket(Base, TimestampMixin): ...
# class TicketResponse(Base, TimestampMixin): ... 