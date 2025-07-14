from sqlalchemy import Column, String, Integer, Boolean, Float, ForeignKey, Text, Enum, Table, DateTime, JSON
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, Enum, ForeignKey, Table
from sqlalchemy.orm import relationship
from database import Base
from .base import TimestampMixin
import enum


class PropertyStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"
    SOLD = "sold"
    PROCESSING = "processing"  # Добавляем статус для объявлений в процессе съемки 360


# Связующая таблица для связи многие ко многим между Property и Category
class PropertyCategory(Base):
    __tablename__ = "property_category"
    
    property_id = Column(Integer, ForeignKey("properties.id"), primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), primary_key=True)
    
    property = relationship("Property", back_populates="property_categories")
    category = relationship("Category", back_populates="property_categories")


class Property(Base, TimestampMixin):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    description = Column(Text)
    price = Column(Float)
    address = Column(String(255))
    city = Column(String(100))
    
    # Google Maps координаты
    latitude = Column(Float, nullable=True)  # Широта
    longitude = Column(Float, nullable=True)  # Долгота
    formatted_address = Column(String(500), nullable=True)  # Отформатированный адрес от Google
    
    area = Column(Float)
    status = Column(Enum(PropertyStatus), default=PropertyStatus.DRAFT)
    is_featured = Column(Boolean, default=False)
    
    # 360° панорама поля
    tour_360_url = Column(String(255), nullable=True)  # URL для старой совместимости
    tour_360_file_id = Column(String(100), nullable=True)  # ID файла панорамы
    tour_360_original_url = Column(String(255), nullable=True)  # Путь к оригинальному файлу
    tour_360_optimized_url = Column(String(255), nullable=True)  # Путь к оптимизированному файлу
    tour_360_preview_url = Column(String(255), nullable=True)  # Путь к превью
    tour_360_thumbnail_url = Column(String(255), nullable=True)  # Путь к миниатюре
    tour_360_metadata = Column(Text, nullable=True)  # JSON с метаданными панорамы
    tour_360_uploaded_at = Column(DateTime, nullable=True)  # Дата загрузки панорамы
    
    type = Column(String(50), default="apartment")  # Добавляем поле типа недвижимости
    
    # Дополнительные поля для фильтрации
    rooms = Column(Integer, nullable=True)  # Количество комнат
    floor = Column(Integer, nullable=True)  # Этаж
    building_floors = Column(Integer, nullable=True)  # Этажность здания
    has_balcony = Column(Boolean, default=False)  # Наличие балкона
    has_furniture = Column(Boolean, default=False)  # Наличие мебели
    has_renovation = Column(Boolean, default=False)  # Наличие ремонта
    has_parking = Column(Boolean, default=False)  # Наличие парковки
    
    # Новые поля удобств
    has_elevator = Column(Boolean, default=False)  # Лифт
    has_security = Column(Boolean, default=False)  # Охрана
    has_internet = Column(Boolean, default=False)  # Интернет
    has_air_conditioning = Column(Boolean, default=False)  # Кондиционер
    has_heating = Column(Boolean, default=False)  # Отопление
    has_yard = Column(Boolean, default=False)  # Двор/сад
    has_pool = Column(Boolean, default=False)  # Бассейн
    has_gym = Column(Boolean, default=False)  # Спортзал
    bathroom_type = Column(String(50), nullable=True)  # Тип санузла
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)  # Категория
    
    notes = Column(String(255), nullable=True)  # Поле для хранения даты съемки
    views = Column(Integer, default=0)  # Счетчик просмотров объявления
    
    # Поля для медиа-сервера
    media_id = Column(String(19), nullable=True)  # ID медиа на внешнем сервере
    images_data = Column(JSON, nullable=True)  # JSON данные об изображениях
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="properties")
    
    # Связь с PropertyCategory для класса PropertyCategory
    property_categories = relationship("PropertyCategory", back_populates="property")
    
    # Связь с Category через PropertyCategory
    categories = relationship(
        "Category",
        secondary="property_category",  # Указываем название таблицы как строку
        viewonly=True  # Только для чтения, чтобы избежать конфликтов
    )
    images = relationship("PropertyImage", back_populates="property")
    favorites = relationship("Favorite", back_populates="property")

    # Метод для проверки наличия 360° панорамы
    def has_360_tour(self) -> bool:
        """Проверяет, есть ли у объявления 360° панорама"""
        return bool(self.tour_360_file_id or self.tour_360_url)
    
    def get_360_tour_url(self) -> str:
        """Возвращает URL для отображения 360° панорамы (приоритет оптимизированной версии)"""
        if self.tour_360_optimized_url:
            return self.tour_360_optimized_url
        elif self.tour_360_original_url:
            return self.tour_360_original_url
        elif self.tour_360_url:
            return self.tour_360_url
        return None

    # Метод для преобразования модели в словарь с правильной сериализацией всех полей
    def to_dict(self):
        result = {
            "id": self.id,
            "owner_id": self.owner_id,
            "title": self.title,
            "description": self.description,
            "price": self.price,
            "address": self.address,
            "city": self.city,
            "area": self.area,
            
            # Добавляем координаты в сериализацию
            "latitude": self.latitude,
            "longitude": self.longitude,
            "formatted_address": self.formatted_address,
            
            "status": self.status.value if self.status else "draft",
            "is_featured": self.is_featured,
            "tour_360_url": self.tour_360_url,
            "tour_360_file_id": self.tour_360_file_id,
            "tour_360_original_url": self.tour_360_original_url,
            "tour_360_optimized_url": self.tour_360_optimized_url,
            "tour_360_preview_url": self.tour_360_preview_url,
            "tour_360_thumbnail_url": self.tour_360_thumbnail_url,
            "tour_360_uploaded_at": self.tour_360_uploaded_at.isoformat() if self.tour_360_uploaded_at else None,
            "has_360_tour": self.has_360_tour(),
            "tour_360_display_url": self.get_360_tour_url(),
            "notes": self.notes,
            "views": self.views,
            "type": self.type,
            
            # Поля медиа-сервера
            "media_id": self.media_id,
            "images_data": self.images_data,
            
            "rooms": self.rooms,
            "floor": self.floor,
            "building_floors": self.building_floors,
            "has_furniture": self.has_furniture,
            "has_balcony": self.has_balcony,
            "has_renovation": self.has_renovation,
            "has_parking": self.has_parking,
            "has_elevator": self.has_elevator,
            "has_security": self.has_security,
            "has_internet": self.has_internet,
            "has_air_conditioning": self.has_air_conditioning,
            "has_heating": self.has_heating,
            "has_yard": self.has_yard,
            "has_pool": self.has_pool,
            "has_gym": self.has_gym,
            "bathroom_type": self.bathroom_type,
            "category_id": self.category_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        # Сериализация связанных объектов
        if hasattr(self, "owner") and self.owner:
            result["owner"] = {
                "id": self.owner.id,
                "email": self.owner.email,
                "full_name": self.owner.full_name,
                "role": str(self.owner.role) if hasattr(self.owner, "role") else None,
                "is_active": self.owner.is_active
            }
        
        if hasattr(self, "categories") and self.categories:
            result["categories"] = [
                {
                    "id": cat.id,
                    "name": cat.name,
                    "description": cat.description,
                    "created_at": cat.created_at.isoformat() if hasattr(cat, "created_at") and cat.created_at else None
                } for cat in self.categories
            ]
            
        if hasattr(self, "images") and self.images:
            result["images"] = [
                {
                    "id": img.id,
                    "url": img.url,
                    "is_main": img.is_main,
                    "property_id": img.property_id if hasattr(img, "property_id") else self.id,
                    "created_at": img.created_at.isoformat() if hasattr(img, "created_at") and img.created_at else None
                } for img in self.images
            ]
            
        return result


class PropertyImage(Base, TimestampMixin):
    __tablename__ = "property_images"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(255))
    is_main = Column(Boolean, default=False)
    
    property_id = Column(Integer, ForeignKey("properties.id"))
    property = relationship("Property", back_populates="images")


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True)
    description = Column(String(255), nullable=True)
    
    # Связь с PropertyCategory для класса PropertyCategory
    property_categories = relationship("PropertyCategory", back_populates="category")
    
    # Связь с Property через PropertyCategory
    properties = relationship(
        "Property",
        secondary="property_category",  # Указываем название таблицы как строку
        viewonly=True  # Только для чтения, чтобы избежать конфликтов
    )


class Favorite(Base, TimestampMixin):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(Integer, ForeignKey("users.id"))
    property_id = Column(Integer, ForeignKey("properties.id"))
    
    user = relationship("User", back_populates="favorites")
    property = relationship("Property", back_populates="favorites") 