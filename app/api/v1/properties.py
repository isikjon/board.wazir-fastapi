from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app import models, schemas, services
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.Property])
def read_properties(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    category_id: int = None,
    city: str = None,
    min_price: float = None,
    max_price: float = None,
    min_area: float = None,
    max_area: float = None,
    search: str = None,
) -> Any:
    query = db.query(models.Property)
    
    if category_id:
        query = query.filter(models.Property.categories.any(models.Category.id == category_id))
    
    if city:
        query = query.filter(models.Property.city == city)
    
    if min_price is not None:
        query = query.filter(models.Property.price >= min_price)
    
    if max_price is not None:
        query = query.filter(models.Property.price <= max_price)
        
    if min_area is not None:
        query = query.filter(models.Property.area >= min_area)
    
    if max_area is not None:
        query = query.filter(models.Property.area <= max_area)
    
    if search:
        query = query.filter(
            or_(
                models.Property.title.ilike(f"%{search}%"),
                models.Property.description.ilike(f"%{search}%"),
                models.Property.address.ilike(f"%{search}%"),
            )
        )
    
    properties = query.offset(skip).limit(limit).all()
    return properties


@router.post("/", response_model=schemas.Property)
def create_property(
    *,
    db: Session = Depends(deps.get_db),
    property_in: schemas.PropertyCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    property = services.property.create_with_owner(
        db=db, obj_in=property_in, owner_id=current_user.id
    )
    return property


@router.get("/my", response_model=List[schemas.Property])
def read_user_properties(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    properties = services.property.get_multi_by_owner(
        db=db, owner_id=current_user.id, skip=skip, limit=limit
    )
    return properties


@router.get("/{property_id}", response_model=schemas.Property)
def read_property(
    *,
    db: Session = Depends(deps.get_db),
    property_id: int,
) -> Any:
    property = services.property.get(db=db, id=property_id)
    if not property:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    return property


@router.put("/{property_id}", response_model=schemas.Property)
def update_property(
    *,
    db: Session = Depends(deps.get_db),
    property_id: int,
    property_in: schemas.PropertyUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    property = services.property.get(db=db, id=property_id)
    if not property:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    if property.owner_id != current_user.id and not services.user.is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    
    property = services.property.update(db=db, db_obj=property, obj_in=property_in)
    
    if property_in.category_ids is not None:
        property = services.property.update_property_categories(
            db=db, db_obj=property, category_ids=property_in.category_ids
        )
    
    return property


@router.delete("/{property_id}", response_model=schemas.Property)
def delete_property(
    *,
    db: Session = Depends(deps.get_db),
    property_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    property = services.property.get(db=db, id=property_id)
    if not property:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    if property.owner_id != current_user.id and not services.user.is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    
    property = services.property.remove(db=db, id=property_id)
    return property


@router.post("/{property_id}/upload-image", response_model=schemas.PropertyImage)
async def upload_property_image(
    *,
    db: Session = Depends(deps.get_db),
    property_id: int,
    is_main: bool = False,
    file: UploadFile = File(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    property = services.property.get(db=db, id=property_id)
    if not property:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    if property.owner_id != current_user.id and not services.user.is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    
    # Логика для сохранения файла и получения URL
    file_location = f"media/properties/{property_id}/{file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(await file.read())
    
    image = services.property_image.create_property_image(
        db=db, url=file_location, property_id=property_id, is_main=is_main
    )
    return image


@router.post("/{property_id}/favorite", response_model=schemas.Msg)
def add_to_favorites(
    *,
    db: Session = Depends(deps.get_db),
    property_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    property = services.property.get(db=db, id=property_id)
    if not property:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    
    if services.favorite.is_favorite(db=db, user_id=current_user.id, property_id=property_id):
        return {"msg": "Объявление уже в избранном"}
    
    services.favorite.create_favorite(db=db, user_id=current_user.id, property_id=property_id)
    return {"msg": "Объявление добавлено в избранное"}


@router.delete("/{property_id}/favorite", response_model=schemas.Msg)
def remove_from_favorites(
    *,
    db: Session = Depends(deps.get_db),
    property_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    property = services.property.get(db=db, id=property_id)
    if not property:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    
    services.favorite.remove_favorite(db=db, user_id=current_user.id, property_id=property_id)
    return {"msg": "Объявление удалено из избранного"}


@router.post("/{property_id}/tour", response_model=schemas.Property)
def update_property_tour(
    *,
    db: Session = Depends(deps.get_db),
    property_id: int,
    tour_data: dict = Body(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Обновляет URL 3D-тура для объекта недвижимости
    """
    property = services.property.get(db=db, id=property_id)
    if not property:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    
    # Проверяем права доступа: только владелец или админ могут обновлять
    if property.owner_id != current_user.id and not services.user.is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    
    # Обновляем только поле tour_360_url
    update_data = {"tour_360_url": tour_data.get("tour_url")}
    property = services.property.update(db=db, db_obj=property, obj_in=update_data)
    
    return property 