from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app import models, schemas, services
from app.api import deps
from app.models.user import UserRole
from app.utils.media_uploader import media_uploader

router = APIRouter()

@router.post("/", response_model=schemas.Property)
def create_property(
    *,
    request: Request,
    db: Session = Depends(deps.get_db),
    property_in: schemas.PropertyCreate,
) -> Any:
    """
    Создание нового объявления о недвижимости
    """
    # Получаем текущего пользователя
    current_user = deps.get_current_active_user(request, db)
    
    # Логируем процесс создания объявления
    print(f"DEBUG: Создание нового объявления от пользователя {current_user.id}")
    print(f"DEBUG: Данные объявления: {property_in}")
    
    # Проверяем валидность данных
    if not property_in.category_ids or len(property_in.category_ids) == 0:
        print("DEBUG: Отсутствуют category_ids, устанавливаем значение по умолчанию [1]")
        property_in.category_ids = [1]  # По умолчанию - Продажа
        
    # Убедимся, что status имеет правильное значение из enum
    print(f"DEBUG: Статус объявления: {property_in.status}")
    
    # Проверяем наличие URL изображений
    if not property_in.photo_urls or len(property_in.photo_urls) == 0:
        print("DEBUG: Отсутствуют фотографии объявления")
        raise HTTPException(
            status_code=400,
            detail="Для создания объявления необходимо загрузить минимум 2 фотографии"
        )
    
    try:
        # Создаем объект недвижимости
        property = services.property.create_with_owner(
            db=db, obj_in=property_in, owner_id=current_user.id
        )
        print(f"DEBUG: Объявление успешно создано с ID {property.id}")
        print(f"DEBUG: Созданные изображения: {[img.url for img in property.images]}")
        
        # Радикальное решение - возвращаем ответ в точном соответствии с требуемой схемой
        # Почему-то FastAPI обходит наш метод to_dict и пытается сериализовать по-своему
        # Проблема в том, что указан response_model=schemas.Property в декораторе route
        
        # Чтобы обойти ошибку, мы теперь возвращаем все поля, которые требует сериализатор
        from fastapi.responses import JSONResponse
        
        # Мы не используем response_model FastAPI, а возвращаем ПРЯМОЙ JSONResponse
        return JSONResponse(
            status_code=200,
            content={
                "id": property.id,
                "title": property.title,
                "description": property.description,
                "price": property.price,
                "address": property.address,
                "city": property.city,
                "area": property.area,
                "status": property.status.value if property.status else "draft",
                "created_at": property.created_at.isoformat() if property.created_at else None,
                "updated_at": property.updated_at.isoformat() if property.updated_at else None,
                "owner_id": property.owner_id,
                "owner": {
                    "id": property.owner.id,
                    "email": property.owner.email,
                    "full_name": property.owner.full_name,
                    "is_active": property.owner.is_active
                },
                "success": True,
                "message": f"Объявление успешно создано с ID {property.id}"
            }
        )
    except Exception as e:
        print(f"ERROR: Ошибка при создании объявления: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании объявления: {str(e)}"
        )

@router.get("/", response_model=List[schemas.Property])
def read_properties(
    request: Request,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Получение списка объявлений
    """
    current_user = deps.get_current_active_user(request, db)
    properties = services.property.get_multi(db, skip=skip, limit=limit)
    return properties

@router.get("/my", response_model=List[schemas.Property])
def read_user_properties(
    request: Request,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Получение объявлений текущего пользователя
    """
    current_user = deps.get_current_active_user(request, db)
    properties = services.property.get_multi_by_owner(
        db=db, owner_id=current_user.id, skip=skip, limit=limit
    )
    return properties

# Модель для обновления данных 360° панорамы
class Property360Update(BaseModel):
    tour_360_url: str
    notes: Optional[str] = None

@router.get("/{property_id}/360", response_model=Property360Update)
def get_property_360(
    property_id: int,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Получение данных 360° панорамы для объявления
    """
    current_user = deps.get_current_active_user(request, db)
    property = services.property.get(db=db, id=property_id)
    
    if not property:
        raise HTTPException(
            status_code=404,
            detail="Объявление не найдено"
        )
    
    # Проверяем права доступа (владелец или администратор)
    if property.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Недостаточно прав для просмотра данных 360° панорамы"
        )
    
    return {
        "tour_360_url": property.tour_360_url or "",
        "notes": property.notes or ""
    }

@router.post("/{property_id}/360", response_model=Property360Update)
def update_property_360(
    property_id: int,
    update_data: Property360Update,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Обновление данных 360° панорамы для объявления
    """
    current_user = deps.get_current_active_user(request, db)
    
    print(f"DEBUG: Попытка обновления 360° для объявления {property_id}")
    print(f"DEBUG: Данные для обновления: {update_data}")
    print(f"DEBUG: Текущий пользователь: {current_user.id}, имя: {current_user.full_name}, роль: {current_user.role}")
    
    try:
        property = services.property.get(db=db, id=property_id)
        
        if not property:
            print(f"DEBUG: Объявление {property_id} не найдено")
            raise HTTPException(
                status_code=404,
                detail="Объявление не найдено"
            )
        
        print(f"DEBUG: Объявление найдено, ID: {property.id}, владелец: {property.owner_id}")
        
        # Проверяем права доступа (владелец или администратор)
        if property.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
            print(f"DEBUG: Недостаточно прав для обновления 360° панорамы, владелец: {property.owner_id}, текущий пользователь: {current_user.id}")
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав для обновления 360° панорамы"
            )
        
        print(f"DEBUG: Права доступа подтверждены, обновляем данные 360° панорамы")
        
        # Обновляем данные 360° панорамы
        property.tour_360_url = update_data.tour_360_url
        if update_data.notes:
            property.notes = update_data.notes
        
        db.commit()
        db.refresh(property)
        print(f"DEBUG: Данные 360° панорамы успешно обновлены, URL: {property.tour_360_url}")
    
    except HTTPException as http_ex:
        print(f"DEBUG: HTTPException: {http_ex.detail}, status_code: {http_ex.status_code}")
        raise
    except Exception as e:
        print(f"DEBUG: Неожиданная ошибка при обновлении 360° панорамы: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обновлении 360° панорамы: {str(e)}"
        )
    
    return {
        "tour_360_url": property.tour_360_url or "",
        "notes": property.notes or ""
    }

@router.post("/{property_id}/approve", response_model=dict)
def approve_property(
    property_id: int,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Одобрение объявления администратором
    """
    current_user = deps.get_current_active_user(request, db)
    
    print(f"DEBUG: Попытка одобрения объявления {property_id}")
    print(f"DEBUG: Текущий пользователь: {current_user.id}, имя: {current_user.full_name}, роль: {current_user.role}")
    
    try:
        # Проверяем права пользователя (только администратор может одобрять объявления)
        if current_user.role != UserRole.ADMIN:
            print(f"DEBUG: Недостаточно прав для одобрения объявления, роль пользователя: {current_user.role}")
            raise HTTPException(
                status_code=403,
                detail="Только администратор может одобрять объявления"
            )
        
        # Получаем объявление из базы данных
        property = services.property.get(db=db, id=property_id)
        
        if not property:
            print(f"DEBUG: Объявление {property_id} не найдено")
            raise HTTPException(
                status_code=404,
                detail="Объявление не найдено"
            )
        
        print(f"DEBUG: Объявление найдено, ID: {property.id}, статус: {property.status}")
        
        # Меняем статус объявления на "active" (активно/одобрено)
        property_data = {"status": "active"}
        updated_property = services.property.update(db=db, db_obj=property, obj_in=property_data)
        
        print(f"DEBUG: Объявление успешно одобрено, новый статус: {updated_property.status}")
        
        return {
            "success": True,
            "message": "Объявление успешно одобрено",
            "property_id": property_id
        }
        
    except HTTPException as http_ex:
        print(f"DEBUG: HTTPException: {http_ex.detail}, status_code: {http_ex.status_code}")
        raise
    except Exception as e:
        print(f"DEBUG: Неожиданная ошибка при одобрении объявления: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при одобрении объявления: {str(e)}"
        )

@router.post("/with-media", response_model=dict)
async def create_property_with_media(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    address: str = Form(...),
    city: str = Form("Бишкек"),
    category: str = Form("Продажа"),
    area: Optional[float] = Form(None),
    floor: Optional[int] = Form(None),
    building_floors: Optional[int] = Form(None),
    rooms: Optional[str] = Form(None),
    apartment_type: Optional[str] = Form(None),
    house_type: Optional[str] = Form(None),
    # Google Maps координаты
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    formatted_address: Optional[str] = Form(None),
    # Дополнительные опции
    has_balcony: Optional[bool] = Form(False),
    has_furniture: Optional[bool] = Form(False),
    has_renovation: Optional[bool] = Form(False),
    has_parking: Optional[bool] = Form(False),
    has_elevator: Optional[bool] = Form(False),
    # 360° тур
    request_360_tour: Optional[str] = Form(None),
    # Контактная информация
    full_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    photos: List[UploadFile] = File(...),
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Создание нового объявления с загрузкой фотографий на медиа-сервер
    """
    try:
        # Получаем текущего пользователя
        print("DEBUG: Начинаем получение текущего пользователя...")
        current_user = deps.get_current_active_user(request, db)
        
        # ДОПОЛНИТЕЛЬНАЯ ОТЛАДКА - проверяем тип объекта
        print(f"DEBUG: Тип current_user: {type(current_user)}")
        print(f"DEBUG: current_user является словарем? {isinstance(current_user, dict)}")
        print(f"DEBUG: current_user содержание: {current_user}")
        
        if isinstance(current_user, dict):
            print("ERROR: current_user является словарем, но должен быть объектом User!")
            raise HTTPException(
                status_code=401,
                detail="Ошибка аутентификации: получен неправильный тип пользователя"
            )
        
        if not hasattr(current_user, 'id'):
            print(f"ERROR: current_user не имеет атрибута 'id'. Атрибуты: {dir(current_user)}")
            raise HTTPException(
                status_code=401,
                detail="Ошибка аутентификации: объект пользователя не имеет ID"
            )
        
        print(f"DEBUG: Создание объявления с медиа от пользователя {current_user.id}")
        print(f"DEBUG: Получены данные - title: {title}, price: {price}, city: {city}")
        
        # Проверяем фотографии
        if not photos or len(photos) < 2:
            raise HTTPException(
                status_code=400,
                detail="Необходимо загрузить минимум 2 фотографии"
            )
        
        # Проверяем типы файлов
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
        for photo in photos:
            if photo.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Неподдерживаемый тип файла: {photo.content_type}"
                )
        
        # Загружаем изображения на медиа-сервер
        print("DEBUG: Загрузка изображений на медиа-сервер...")
        upload_result = await media_uploader.upload_property_images(photos)
        
        if upload_result["status"] != "success":
            raise HTTPException(
                status_code=400,
                detail=f"Ошибка загрузки изображений: {upload_result['message']}"
            )
        
        property_media_id = upload_result["property_id"]
        images_data = upload_result["files"]
        
        print(f"DEBUG: Изображения загружены, media_id: {property_media_id}")
        
        # Определяем количество комнат
        rooms_count = None
        if rooms:
            if rooms == "studio":
                rooms_count = 0
            elif rooms.isdigit():
                rooms_count = int(rooms)
            elif rooms == "5+":
                rooms_count = 5
        
        # Создаем объект PropertyCreate с медиа данными (БЕЗ media_id и images_data для схемы)
        property_data = schemas.PropertyCreate(
            title=title,
            description=description,
            price=price,
            address=address,
            city=city,
            area=area or 0.0,
            rooms=rooms_count,
            floor=floor,
            building_floors=building_floors,
            has_balcony=has_balcony,
            has_furniture=has_furniture,
            has_renovation=has_renovation,
            has_parking=has_parking,
            has_elevator=has_elevator,
            photo_urls=[img["urls"]["medium"] for img in images_data],
            category_ids=[1],  # По умолчанию - Продажа
            latitude=latitude,
            longitude=longitude,
            formatted_address=formatted_address,
            type=apartment_type or house_type or "apartment"
        )
        
        # Создаем объявление
        property = services.property.create_with_owner(
            db=db, obj_in=property_data, owner_id=current_user.id
        )
        
        # ОТДЕЛЬНО сохраняем медиа-данные
        property.media_id = property_media_id
        property.images_data = images_data
        db.commit()
        db.refresh(property)
        
        print(f"DEBUG: Объявление создано с ID {property.id}, media_id: {property.media_id}")
        
        return {
            "status": "success",
            "property_id": property.id,
            "media_id": property_media_id,
            "images_count": len(images_data),
            "message": "Объявление успешно создано с изображениями"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Общая ошибка при создании объявления с медиа: {e}")
        print(f"ERROR: Тип ошибки: {type(e)}")
        print(f"ERROR: Полная информация об ошибке: {repr(e)}")
        
        # Пытаемся удалить загруженные изображения при ошибке
        if 'property_media_id' in locals():
            try:
                await media_uploader.delete_property_images(property_media_id)
                print(f"DEBUG: Загруженные изображения удалены после ошибки")
            except:
                print(f"DEBUG: Не удалось удалить изображения после ошибки")
        
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании объявления: {str(e)}"
        )
