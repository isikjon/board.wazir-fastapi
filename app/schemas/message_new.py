from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.message import MessageStatus
from app.models.support import TicketStatus


class MessageBase(BaseModel):
    content: str
    recipient_id: int
    status: Optional[MessageStatus] = MessageStatus.SENT


class MessageCreate(MessageBase):
    pass


class MessageInDBBase(MessageBase):
    id: int
    sender_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageInDB(MessageInDBBase):
    pass


class Message(MessageInDBBase):
    sender: Dict[str, Any]
    recipient: Dict[str, Any]


class TicketBase(BaseModel):
    subject: str
    description: str
    status: Optional[TicketStatus] = TicketStatus.OPEN


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None


class TicketInDBBase(TicketBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TicketInDB(TicketInDBBase):
    pass


class TicketResponseBase(BaseModel):
    content: str
    is_from_admin: Optional[bool] = False


class TicketResponseCreate(TicketResponseBase):
    ticket_id: int


class TicketResponseInDB(TicketResponseBase):
    id: int
    ticket_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TicketResponse(TicketResponseInDB):
    pass


class Ticket(TicketInDBBase):
    user: Dict[str, Any]
    responses: List[TicketResponse] = [] 
    chat_id: Optional[int] = None
