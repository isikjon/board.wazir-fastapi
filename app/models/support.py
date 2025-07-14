from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from database import Base
from .base import TimestampMixin
import enum


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class SupportTicket(Base, TimestampMixin):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(255))
    description = Column(Text)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="support_tickets")
    
    responses = relationship("TicketResponse", back_populates="ticket", cascade="all, delete-orphan")


class TicketResponse(Base, TimestampMixin):
    __tablename__ = "support_messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    is_from_admin = Column(Boolean, default=False)
    
    ticket_id = Column(Integer, ForeignKey("support_tickets.id", ondelete="CASCADE"))
    ticket = relationship("SupportTicket", back_populates="responses")
