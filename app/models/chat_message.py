from sqlalchemy import Column, Integer, ForeignKey, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
from database import Base
from .base import TimestampMixin
import datetime

class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"))
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    content = Column(Text)
    is_read = Column(Boolean, default=False)

    # Явно указываем соединение для отношения
    sender = relationship(
        "app.models.user.User", 
        foreign_keys=[sender_id],
        primaryjoin="ChatMessage.sender_id == app.models.user.User.id",
        backref="sent_chat_messages"
    )
    chat = relationship(
        "app.models.chat.AppChatModel", 
        foreign_keys=[chat_id],
        primaryjoin="ChatMessage.chat_id == app.models.chat.AppChatModel.id",
        backref="chat_messages"
    )
