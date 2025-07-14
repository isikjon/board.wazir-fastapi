from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime
from app.models.request import RequestStatus, RequestType


class RequestBase(BaseModel):
    title: str
    description: Optional[str] = None
    type: RequestType = RequestType.OTHER
    appointment_date: Optional[datetime] = None
    property_id: Optional[int] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    is_urgent: Optional[bool] = False


class RequestCreate(RequestBase):
    pass


class RequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[RequestType] = None
    status: Optional[RequestStatus] = None
    appointment_date: Optional[datetime] = None
    property_id: Optional[int] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    is_urgent: Optional[bool] = None


class RequestInDB(RequestBase):
    id: int
    status: RequestStatus
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class Request(RequestInDB):
    user: Optional[Any] = None  
    property: Optional[Any] = None
    
    model_config = ConfigDict(from_attributes=True) 