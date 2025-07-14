from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas, services
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.Category])
def read_categories(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    categories = services.category.get_multi(db, skip=skip, limit=limit)
    return categories


@router.post("/", response_model=schemas.Category)
def create_category(
    *,
    db: Session = Depends(deps.get_db),
    category_in: schemas.CategoryCreate,
    current_user: models.User = Depends(deps.get_current_active_admin),
) -> Any:
    category = services.category.get_by_name(db, name=category_in.name)
    if category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Категория с таким названием уже существует",
        )
    category = services.category.create(db=db, obj_in=category_in)
    return category


@router.get("/{category_id}", response_model=schemas.Category)
def read_category(
    *,
    db: Session = Depends(deps.get_db),
    category_id: int,
) -> Any:
    category = services.category.get(db=db, id=category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category


@router.put("/{category_id}", response_model=schemas.Category)
def update_category(
    *,
    db: Session = Depends(deps.get_db),
    category_id: int,
    category_in: schemas.CategoryUpdate,
    current_user: models.User = Depends(deps.get_current_active_admin),
) -> Any:
    category = services.category.get(db=db, id=category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    
    if category_in.name != category.name:
        existing = services.category.get_by_name(db, name=category_in.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Категория с таким названием уже существует",
            )
    
    category = services.category.update(db=db, db_obj=category, obj_in=category_in)
    return category


@router.delete("/{category_id}", response_model=schemas.Category)
def delete_category(
    *,
    db: Session = Depends(deps.get_db),
    category_id: int,
    current_user: models.User = Depends(deps.get_current_active_admin),
) -> Any:
    category = services.category.get(db=db, id=category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    
    category = services.category.remove(db=db, id=category_id)
    return category 