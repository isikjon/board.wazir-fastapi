from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps
from app.services.category import general_category

router = APIRouter()


@router.get("/", response_model=List[schemas.GeneralCategory])
def get_categories(
    db: Session = Depends(deps.get_db),
    parent_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
):
    if parent_id is not None:
        categories = general_category.get_active_categories(db, parent_id=parent_id)
    else:
        categories = general_category.get_top_level_categories(db)
    
    return categories[skip : skip + limit]


@router.get("/top-level", response_model=List[schemas.GeneralCategory])
def get_top_level_categories(
    db: Session = Depends(deps.get_db)
):
    return general_category.get_top_level_categories(db)


@router.get("/{category_id}", response_model=schemas.GeneralCategory)
def get_category(
    category_id: int,
    db: Session = Depends(deps.get_db),
    include_children: bool = False
):
    if include_children:
        category = general_category.get_category_with_children(db, category_id)
    else:
        category = general_category.get(db, id=category_id)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена"
        )
    
    return category


@router.get("/slug/{slug}", response_model=schemas.GeneralCategory)
def get_category_by_slug(
    slug: str,
    db: Session = Depends(deps.get_db),
    include_children: bool = False
):
    category = general_category.get_by_slug(db, slug=slug)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена"
        )
    
    if include_children:
        category.children = general_category.get_active_categories(db, parent_id=category.id)
    
    return category


@router.post("/", response_model=schemas.GeneralCategory)
def create_category(
    category_in: schemas.GeneralCategoryCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_admin),
):
    existing = general_category.get_by_slug(db, slug=category_in.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Категория с таким slug уже существует"
        )
    
    return general_category.create(db=db, obj_in=category_in)


@router.put("/{category_id}", response_model=schemas.GeneralCategory)
def update_category(
    category_id: int,
    category_in: schemas.GeneralCategoryUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_admin),
):
    category = general_category.get(db, id=category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена"
        )
    
    if category_in.slug and category_in.slug != category.slug:
        existing = general_category.get_by_slug(db, slug=category_in.slug)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Категория с таким slug уже существует"
            )
    
    return general_category.update(db=db, db_obj=category, obj_in=category_in)


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_admin),
):
    category = general_category.get(db, id=category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена"
        )
    
    general_category.remove(db=db, id=category_id)
    return {"message": "Категория удалена"}


@router.post("/init-default")
def init_default_categories(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_admin),
):
    general_category.create_default_categories(db)
    return {"message": "Категории по умолчанию созданы"} 