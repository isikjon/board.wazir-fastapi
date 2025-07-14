from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.property import PropertyStatus


class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    name: Optional[str] = None


class CategoryInDBBase(CategoryBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Category(CategoryInDBBase):
    pass


class PropertyImageBase(BaseModel):
    url: str
    is_main: Optional[bool] = False


class PropertyImageCreate(PropertyImageBase):
    pass


class PropertyImageUpdate(PropertyImageBase):
    url: Optional[str] = None


class PropertyImageInDBBase(PropertyImageBase):
    id: int
    property_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PropertyImage(PropertyImageInDBBase):
    pass


class PropertyBase(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    address: str
    city: str
    area: float
    status: Optional[PropertyStatus] = PropertyStatus.PENDING
    is_featured: Optional[bool] = False
    tour_360_url: Optional[str] = None
    type: Optional[str] = "apartment"
    
    # Google Maps координаты
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    formatted_address: Optional[str] = None


class PropertyCreate(PropertyBase):
    category_ids: List[int]
    photo_urls: Optional[List[str]] = None
    rooms: Optional[int] = None
    floor: Optional[int] = None
    building_floors: Optional[int] = None
    has_furniture: Optional[bool] = False
    has_balcony: Optional[bool] = False
    has_renovation: Optional[bool] = False
    has_parking: Optional[bool] = False
    has_elevator: Optional[bool] = False
    has_security: Optional[bool] = False
    has_internet: Optional[bool] = False
    has_air_conditioning: Optional[bool] = False
    has_heating: Optional[bool] = False
    has_yard: Optional[bool] = False
    has_pool: Optional[bool] = False
    has_gym: Optional[bool] = False
    bathroom_type: Optional[str] = None
    category_id: Optional[int] = None


class PropertyUpdate(PropertyBase):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    area: Optional[float] = None
    category_ids: Optional[List[int]] = None


class PropertyInDBBase(PropertyBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PropertyInDB(PropertyInDBBase):
    pass


class Property(PropertyInDBBase):
    categories: List[Category] = []
    images: List[PropertyImage] = []
    owner: Dict[str, Any]


class FavoriteBase(BaseModel):
    property_id: int


class FavoriteCreate(FavoriteBase):
    pass


class FavoriteInDBBase(FavoriteBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Favorite(FavoriteInDBBase):
    property: Property 