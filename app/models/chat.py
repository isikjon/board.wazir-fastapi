from sqlalchemy import Column, Integer, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from database import Base
from .base import TimestampMixin
from app.models.user import User


class AppChatModel(Base, TimestampMixin):
    """
    Переименовано во избежание конфликта с моделями в models/chat.py
    """
    __tablename__ = "chats"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    user2_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    
    # Отключение отношений для предотвращения конфликтов
    """
    user1 = relationship(
        User,
        foreign_keys=[user1_id],
        backref="chats_as_user1"
    )
    user2 = relationship(
        User,
        foreign_keys=[user2_id],
        backref="chats_as_user2"
    )
    messages = relationship("ChatMessageModel", back_populates="chat")
    """


class AppChatMessageModel(Base, TimestampMixin):
    """
    Переименовано во избежание конфликта с моделями в models/chat.py
    """
    __tablename__ = "chat_messages"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"))
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    content = Column(Text)
    is_read = Column(Boolean, default=False)
    
    # Отключение отношений для предотвращения конфликтов
    """
    chat = relationship("ChatModel", back_populates="messages")
    sender = relationship("User", backref="chat_messages")
    """ 