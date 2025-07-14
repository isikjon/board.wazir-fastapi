from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class GeneralCategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0
    parent_id: Optional[int] = None
    level: int = 1


class GeneralCategoryCreate(GeneralCategoryBase):
    pass


class GeneralCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    parent_id: Optional[int] = None
    level: Optional[int] = None


class GeneralCategoryInDB(GeneralCategoryBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class GeneralCategory(GeneralCategoryInDB):
    children: Optional[List["GeneralCategory"]] = None 