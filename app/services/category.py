from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc

from app.services.base import CRUDBase
from app.models.category import GeneralCategory
from app.schemas.category import GeneralCategoryCreate, GeneralCategoryUpdate


class CRUDGeneralCategory(CRUDBase[GeneralCategory, GeneralCategoryCreate, GeneralCategoryUpdate]):
    def get_by_slug(self, db: Session, *, slug: str) -> Optional[GeneralCategory]:
        return db.query(GeneralCategory).filter(GeneralCategory.slug == slug).first()
    
    def get_active_categories(self, db: Session, parent_id: Optional[int] = None) -> List[GeneralCategory]:
        query = db.query(GeneralCategory).filter(GeneralCategory.is_active == True)
        if parent_id is not None:
            query = query.filter(GeneralCategory.parent_id == parent_id)
        else:
            query = query.filter(GeneralCategory.parent_id.is_(None))
        return query.order_by(asc(GeneralCategory.sort_order), asc(GeneralCategory.name)).all()
    
    def get_top_level_categories(self, db: Session) -> List[GeneralCategory]:
        return db.query(GeneralCategory).filter(
            GeneralCategory.is_active == True,
            GeneralCategory.level == 1
        ).order_by(asc(GeneralCategory.sort_order), asc(GeneralCategory.name)).all()
    
    def get_category_with_children(self, db: Session, category_id: int) -> Optional[GeneralCategory]:
        category = db.query(GeneralCategory).filter(GeneralCategory.id == category_id).first()
        if category:
            category.children = self.get_active_categories(db, parent_id=category.id)
        return category
    
    def create_default_categories(self, db: Session) -> None:
        default_categories = [
            {"name": "Недвижимость", "slug": "real-estate", "icon": "fas fa-home", "sort_order": 1},
            {"name": "Авто", "slug": "auto", "icon": "fas fa-car", "sort_order": 2},
            {"name": "Работа", "slug": "jobs", "icon": "fas fa-briefcase", "sort_order": 3},
            {"name": "Услуги", "slug": "services", "icon": "fas fa-handshake", "sort_order": 4},
            {"name": "Бытовая техника", "slug": "appliances", "icon": "fas fa-plug", "sort_order": 5},
            {"name": "Мебель", "slug": "furniture", "icon": "fas fa-couch", "sort_order": 6},
            {"name": "Кух товары", "slug": "kitchen", "icon": "fas fa-utensils", "sort_order": 7},
            {"name": "Строительство", "slug": "construction", "icon": "fas fa-hammer", "sort_order": 8},
            {"name": "Растения", "slug": "plants", "icon": "fas fa-leaf", "sort_order": 9},
            {"name": "Вещи", "slug": "items", "icon": "fas fa-box", "sort_order": 10},
            {"name": "Питание", "slug": "food", "icon": "fas fa-utensils", "sort_order": 11},
            {"name": "Магазины", "slug": "shops", "icon": "fas fa-store", "sort_order": 12},
            {"name": "Fast Food", "slug": "fast-food", "icon": "fas fa-pizza-slice", "sort_order": 13},
            {"name": "Одежда", "slug": "clothing", "icon": "fas fa-tshirt", "sort_order": 14},
            {"name": "Красота", "slug": "beauty", "icon": "fas fa-spa", "sort_order": 15},
        ]
        
        for cat_data in default_categories:
            existing = self.get_by_slug(db, slug=cat_data["slug"])
            if not existing:
                category = GeneralCategory(**cat_data)
                db.add(category)
        
        db.commit()


general_category = CRUDGeneralCategory(GeneralCategory) 