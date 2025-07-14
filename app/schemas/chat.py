from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime


class MessageBase(BaseModel):
    content: str


class MessageCreate(MessageBase):
    receiver_id: int


class MessageRead(BaseModel):
    message_id: int


class Message(MessageBase):
    id: int
    sender_id: int
    content: str
    timestamp: datetime = None
    is_read: bool
    chat_id: int = None

    class Config:
        from_attributes = True


class ChatUser(BaseModel):
    id: int
    full_name: str
    
    class Config:
        from_attributes = True


class ChatPreview(BaseModel):
    user: ChatUser
    last_message: Optional[Message] = None
    unread_count: int = 0

    class Config:
        from_attributes = True
