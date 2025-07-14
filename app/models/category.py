from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base
from .base import TimestampMixin


class GeneralCategory(Base, TimestampMixin):
    __tablename__ = "general_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    image_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    
    parent_id = Column(Integer, ForeignKey("general_categories.id"), nullable=True)
    parent = relationship("GeneralCategory", remote_side=[id], back_populates="children")
    children = relationship("GeneralCategory", back_populates="parent")
    
    level = Column(Integer, default=1)
    
    def __repr__(self):
        return f"<GeneralCategory {self.name}>" 