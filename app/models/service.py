from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from database import Base
from .base import TimestampMixin


class ServiceCategory(Base, TimestampMixin):
    """Модель для категорий сервисов"""
    __tablename__ = "service_categories"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)  # Название категории
    slug = Column(String(255), unique=True, nullable=False, index=True)  # URL-слаг для категории
    is_active = Column(Boolean, default=True)  # Активна ли категория
    
    # Связь с карточками заведений
    service_cards = relationship("ServiceCard", back_populates="category")


class ServiceCard(Base, TimestampMixin):
    """Модель для карточек заведений в сервисах"""
    __tablename__ = "service_cards"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)  # Название заведения
    description = Column(Text, nullable=True)  # Описание заведения
    address = Column(String(255), nullable=True)  # Адрес заведения
    phone = Column(String(50), nullable=True)  # Телефон
    email = Column(String(255), nullable=True)  # Email
    website = Column(String(255), nullable=True)  # Веб-сайт
    image_url = Column(String(255), nullable=True)  # Основное изображение (для совместимости)
    is_active = Column(Boolean, default=True)  # Активна ли карточка
    
    # Координаты заведения
    latitude = Column(Float, nullable=True)  # Широта
    longitude = Column(Float, nullable=True)  # Долгота
    
    # Поля для 360° панорам (аналогично Property)
    tour_360_url = Column(String(255), nullable=True)  # URL для старой совместимости
    tour_360_file_id = Column(String(100), nullable=True)  # ID файла панорамы
    tour_360_original_url = Column(String(255), nullable=True)  # Путь к оригинальному файлу
    tour_360_optimized_url = Column(String(255), nullable=True)  # Путь к оптимизированному файлу
    tour_360_preview_url = Column(String(255), nullable=True)  # Путь к превью
    tour_360_thumbnail_url = Column(String(255), nullable=True)  # Путь к миниатюре
    tour_360_metadata = Column(Text, nullable=True)  # JSON с метаданными панорамы
    tour_360_uploaded_at = Column(DateTime, nullable=True)  # Дата загрузки панорамы
    
    # Поля для системы изображений
    photos_uploaded_at = Column(DateTime, nullable=True)  # Дата последней загрузки фотографий
    
    # Связь с категорией
    category_id = Column(Integer, ForeignKey("service_categories.id"), nullable=False)
    category = relationship("ServiceCategory", back_populates="service_cards")
    
    # Связь с изображениями
    images = relationship("ServiceCardImage", back_populates="service_card", cascade="all, delete-orphan")
    
    def has_360_tour(self) -> bool:
        """Проверяет, есть ли у заведения 360° панорама"""
        return bool(self.tour_360_file_id or self.tour_360_url)
    
    def get_360_tour_url(self) -> str:
        """Возвращает URL для 360° панорамы"""
        if self.tour_360_optimized_url:
            return self.tour_360_optimized_url
        return self.tour_360_url


class ServiceCardImage(Base, TimestampMixin):
    """Модель для дополнительных изображений карточек заведений"""
    __tablename__ = "service_card_images"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(255), nullable=False)
    is_main = Column(Boolean, default=False)
    
    service_card_id = Column(Integer, ForeignKey("service_cards.id"), nullable=False)
    service_card = relationship("ServiceCard", back_populates="images") 