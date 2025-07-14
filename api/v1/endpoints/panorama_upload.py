from typing import Any
from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.api import deps
from app import models
from app.utils.panorama_processor import panorama_processor, PanoramaProcessor
from datetime import datetime
import json
import os
import logging
import tempfile
from pathlib import Path
from typing import Optional

# Настройка логирования с эмодзи для лучшей читаемости
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

async def check_admin_access(request: Request, db: Session):
    """Проверка доступа администратора"""
    logger.info("🔐 Проверка доступа администратора...")
    
    auth_token = request.cookies.get('access_token')
    if not auth_token:
        logger.warning("❌ Токен доступа не найден в cookies")
        return RedirectResponse('/admin/login', status_code=303)
    
    try:
        from jose import jwt
        from config import settings
        payload = jwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.debug(f"🔍 Payload токена: {payload}")
        
        if not payload.get("is_admin"):
            logger.warning("❌ Пользователь не является администратором")
            return RedirectResponse('/admin/login', status_code=303)
        
        # Получаем пользователя из базы данных
        user = db.query(models.User).filter(models.User.id == payload["sub"]).first()
        if not user:
            logger.error(f"❌ Пользователь с ID {payload['sub']} не найден в БД")
            return RedirectResponse('/admin/login', status_code=303)
        
        # Дополнительная проверка что пользователь действительно администратор
        if user.role != models.UserRole.ADMIN:
            logger.warning(f"❌ Пользователь {user.email} не является администратором (роль: {user.role})")
            return RedirectResponse('/admin/login', status_code=303)
        
        logger.info(f"✅ Администратор подтвержден: {user.email} (ID: {user.id})")
        return user
        
    except Exception as e:
        logger.error(f"💥 Ошибка проверки доступа администратора: {str(e)}")
        return RedirectResponse('/admin/login', status_code=303)

async def check_company_access(request: Request, db: Session):
    """Проверка доступа компании"""
    logger.info("🏢 Проверка доступа компании...")
    
    auth_token = request.cookies.get('access_token')
    if not auth_token:
        logger.warning("❌ Токен доступа не найден в cookies")
        return RedirectResponse('/companies/login', status_code=303)
    
    try:
        from jose import jwt
        from config import settings
        payload = jwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.debug(f"🔍 Payload токена: {payload}")
        
        if not payload.get("is_company"):
            logger.warning("❌ Пользователь не является компанией")
            return RedirectResponse('/companies/login', status_code=303)
        
        # Получаем пользователя-компанию из базы данных
        user = db.query(models.User).filter(models.User.id == payload["sub"]).first()
        if not user:
            logger.error(f"❌ Пользователь с ID {payload['sub']} не найден в БД")
            return RedirectResponse('/companies/login', status_code=303)
        
        # Дополнительная проверка что пользователь действительно компания
        if user.role != models.UserRole.COMPANY:
            logger.warning(f"❌ Пользователь {user.email} не является компанией (роль: {user.role})")
            return RedirectResponse('/companies/login', status_code=303)
        
        logger.info(f"✅ Компания подтверждена: {user.email} (ID: {user.id})")
        return user
        
    except Exception as e:
        logger.error(f"💥 Ошибка проверки доступа компании: {str(e)}")
        return RedirectResponse('/companies/login', status_code=303)

@router.get("/admin/properties/{property_id}/360")
async def get_admin_panorama_info(
    property_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    """Получение информации о 360° панораме для админки"""
    logger.info(f"📊 Запрос информации о 360° панораме для свойства {property_id} (админка)")
    
    # Проверка доступа администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    try:
        # Получение объявления
        logger.debug(f"🔍 Поиск объявления с ID: {property_id}")
        property_obj = db.query(models.Property).filter(models.Property.id == property_id).first()
        
        if not property_obj:
            logger.error(f"❌ Объявление с ID {property_id} не найдено")
            raise HTTPException(status_code=404, detail="Объявление не найдено")
        
        logger.debug(f"✅ Объявление найдено: {property_obj.title}")
        
        # Формирование ответа с информацией о панораме
        panorama_info = {
            "has_360": bool(property_obj.tour_360_url or property_obj.tour_360_file_id),
            "tour_360_url": property_obj.tour_360_url,
            "tour_360_file_id": property_obj.tour_360_file_id,
            "tour_360_original_url": property_obj.tour_360_original_url,
            "tour_360_optimized_url": property_obj.tour_360_optimized_url,
            "tour_360_preview_url": property_obj.tour_360_preview_url,
            "tour_360_thumbnail_url": property_obj.tour_360_thumbnail_url,
            "tour_360_uploaded_at": property_obj.tour_360_uploaded_at.isoformat() if property_obj.tour_360_uploaded_at else None,
            "tour_360_metadata": json.loads(property_obj.tour_360_metadata) if property_obj.tour_360_metadata else None
        }
        
        logger.info(f"📋 Информация о панораме подготовлена для объявления {property_id}")
        logger.debug(f"📄 Данные панорамы: {json.dumps(panorama_info, indent=2, ensure_ascii=False)}")
        
        return JSONResponse(content=panorama_info)
        
    except Exception as e:
        logger.error(f"💥 Ошибка получения информации о панораме: {str(e)}")
        logger.exception("Полный стек ошибки:")
        raise HTTPException(status_code=500, detail=f"Ошибка получения данных: {str(e)}")

@router.post("/admin/properties/{property_id}/360/upload")
async def upload_admin_panorama(
    property_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db)
):
    logger.info(f"🎯 Начинаем загрузку 360° панорамы для свойства {property_id} (админка)")
    logger.debug(f"📂 Информация о файле: {file.filename}, размер: {file.size if hasattr(file, 'size') else 'неизвестно'}")
    
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        logger.warning("❌ Доступ запрещен - пользователь не администратор")
        return user
    
    try:
        logger.debug(f"🔍 Поиск объявления с ID: {property_id}")
        property_obj = db.query(models.Property).filter(models.Property.id == property_id).first()
        
        if not property_obj:
            logger.error(f"❌ Объявление с ID {property_id} не найдено")
            raise HTTPException(status_code=404, detail="Объявление не найдено")
        
        logger.info(f"✅ Объявление найдено: {property_obj.title}")
        
        logger.info("🔧 Инициализация процессора панорам...")
        processor = PanoramaProcessor()
        
        if property_obj.tour_360_file_id:
            logger.info(f"🗑️ Удаление существующих файлов панорамы: {property_obj.tour_360_file_id}")
            try:
                await processor.delete_panorama_files(property_obj.tour_360_file_id, property_id)
                logger.info("✅ Существующие файлы панорамы удалены")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка удаления существующих файлов: {str(e)}")
        
        logger.info("🎨 Начинаем обработку панорамы...")
        result = await processor.upload_panorama(file, property_id)
        logger.info("🎉 Панорама успешно обработана!")
        
        if not result.get("success"):
            error_message = result.get("message", "Неизвестная ошибка при загрузке панорамы")
            logger.error(f"❌ Ошибка загрузки панорамы: {error_message}")
            raise HTTPException(status_code=500, detail=f"Ошибка загрузки панорамы: {error_message}")
        
        logger.info("💾 Сохранение данных в базу данных...")
        property_obj.tour_360_file_id = result['file_id']
        property_obj.tour_360_original_url = result['urls']['original']
        property_obj.tour_360_optimized_url = result['urls']['optimized']
        property_obj.tour_360_preview_url = result['urls']['preview']
        property_obj.tour_360_thumbnail_url = result['urls']['thumbnail']
        property_obj.tour_360_metadata = json.dumps(result['metadata'], ensure_ascii=False)
        property_obj.tour_360_uploaded_at = datetime.now()
        
        property_obj.tour_360_url = None
        
        logger.debug("📄 Данные для сохранения в БД:")
        logger.debug(f"  file_id: {property_obj.tour_360_file_id}")
        logger.debug(f"  original_url: {property_obj.tour_360_original_url}")
        logger.debug(f"  optimized_url: {property_obj.tour_360_optimized_url}")
        
        logger.debug("🔄 Выполнение коммита в базе данных...")
        db.commit()
        logger.info("✅ Данные успешно сохранены в базе данных")
        
        logger.debug("🔄 Обновление объекта из БД...")
        db.refresh(property_obj)
        
        logger.debug("🔍 Проверка сохраненных данных:")
        logger.debug(f"  tour_360_file_id: {property_obj.tour_360_file_id}")
        logger.debug(f"  tour_360_original_url: {property_obj.tour_360_original_url}")
        logger.debug(f"  tour_360_optimized_url: {property_obj.tour_360_optimized_url}")
        
        response_data = {
            "success": True,
            "message": "360° панорама успешно загружена и обработана",
            "file_id": result['file_id'],
            "urls": {
                "original": result['urls']['original'],
                "optimized": result['urls']['optimized'],
                "preview": result['urls']['preview'],
                "thumbnail": result['urls']['thumbnail']
            },
            "metadata": result['metadata'],
            "uploaded_at": datetime.now().isoformat()
        }
        
        logger.info("🎉 Загрузка 360° панорамы завершена успешно!")
        logger.debug(f"📋 Ответ клиенту: {json.dumps(response_data, indent=2, ensure_ascii=False, default=str)}")
        
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Критическая ошибка при загрузке панорамы: {str(e)}")
        logger.exception("Полный стек ошибки:")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки панорамы: {str(e)}")

@router.delete("/admin/properties/{property_id}/360")
async def delete_admin_panorama(
    property_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    """Удаление 360° панорамы для админки"""
    logger.info(f"🗑️ Удаление 360° панорамы для свойства {property_id} (админка)")
    
    # Проверка доступа администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    try:
        # Получение объявления
        logger.debug(f"🔍 Поиск объявления с ID: {property_id}")
        property_obj = db.query(models.Property).filter(models.Property.id == property_id).first()
        
        if not property_obj:
            logger.error(f"❌ Объявление с ID {property_id} не найдено")
            raise HTTPException(status_code=404, detail="Объявление не найдено")
        
        logger.info(f"✅ Объявление найдено: {property_obj.title}")
        
        # Удаление файлов если они есть
        if property_obj.tour_360_file_id:
            logger.info(f"🗑️ Удаление файлов панорамы: {property_obj.tour_360_file_id}")
            processor = PanoramaProcessor()
            try:
                await processor.delete_panorama_files(property_obj.tour_360_file_id, property_id)
                logger.info("✅ Файлы панорамы удалены")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка удаления файлов: {str(e)}")
        
        # Очистка полей в базе данных
        logger.info("🧹 Очистка полей панорамы в базе данных...")
        property_obj.tour_360_url = None
        property_obj.tour_360_file_id = None
        property_obj.tour_360_original_url = None
        property_obj.tour_360_optimized_url = None
        property_obj.tour_360_preview_url = None
        property_obj.tour_360_thumbnail_url = None
        property_obj.tour_360_metadata = None
        property_obj.tour_360_uploaded_at = None
        
        db.commit()
        logger.info("✅ Панорама успешно удалена из базы данных")
        
        return JSONResponse(content={
            "success": True,
            "message": "360° панорама успешно удалена"
        })
        
    except Exception as e:
        logger.error(f"💥 Ошибка удаления панорамы: {str(e)}")
        logger.exception("Полный стек ошибки:")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления панорамы: {str(e)}")

# Аналогичные эндпоинты для компаний
@router.get("/companies/properties/{property_id}/360")
async def get_company_panorama_info(
    property_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    """Получение информации о 360° панораме для компаний"""
    logger.info(f"📊 Запрос информации о 360° панораме для свойства {property_id} (компания)")
    
    # Проверка доступа компании
    company = await check_company_access(request, db)
    if isinstance(company, RedirectResponse):
        return company
    
    try:
        # Получение объявления
        logger.debug(f"🔍 Поиск объявления с ID: {property_id}")
        property_obj = db.query(models.Property).filter(
            models.Property.id == property_id,
            models.Property.owner_id == company.id
        ).first()
        
        if not property_obj:
            logger.error(f"❌ Объявление с ID {property_id} не найдено или не принадлежит компании")
            raise HTTPException(status_code=404, detail="Объявление не найдено")
        
        logger.debug(f"✅ Объявление найдено: {property_obj.title}")
        
        # Формирование ответа с информацией о панораме
        panorama_info = {
            "has_360": bool(property_obj.tour_360_url or property_obj.tour_360_file_id),
            "tour_360_url": property_obj.tour_360_url,
            "tour_360_file_id": property_obj.tour_360_file_id,
            "tour_360_original_url": property_obj.tour_360_original_url,
            "tour_360_optimized_url": property_obj.tour_360_optimized_url,
            "tour_360_preview_url": property_obj.tour_360_preview_url,
            "tour_360_thumbnail_url": property_obj.tour_360_thumbnail_url,
            "tour_360_uploaded_at": property_obj.tour_360_uploaded_at.isoformat() if property_obj.tour_360_uploaded_at else None,
            "tour_360_metadata": json.loads(property_obj.tour_360_metadata) if property_obj.tour_360_metadata else None
        }
        
        logger.info(f"📋 Информация о панораме подготовлена для объявления {property_id}")
        return JSONResponse(content=panorama_info)
        
    except Exception as e:
        logger.error(f"💥 Ошибка получения информации о панораме: {str(e)}")
        logger.exception("Полный стек ошибки:")
        raise HTTPException(status_code=500, detail=f"Ошибка получения данных: {str(e)}")

@router.post("/companies/properties/{property_id}/360/upload")
async def upload_company_panorama(
    property_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db)
):
    logger.info(f"🎯 Начинаем загрузку 360° панорамы для свойства {property_id} (компания)")
    logger.debug(f"📂 Информация о файле: {file.filename}, размер: {file.size if hasattr(file, 'size') else 'неизвестно'}")
    
    company = await check_company_access(request, db)
    if isinstance(company, RedirectResponse):
        logger.warning("❌ Доступ запрещен - пользователь не компания")
        return company
    
    try:
        logger.debug(f"🔍 Поиск объявления с ID: {property_id}")
        property_obj = db.query(models.Property).filter(
            models.Property.id == property_id,
            models.Property.owner_id == company.id
        ).first()
        
        if not property_obj:
            logger.error(f"❌ Объявление с ID {property_id} не найдено или не принадлежит компании")
            raise HTTPException(status_code=404, detail="Объявление не найдено")
        
        logger.info(f"✅ Объявление найдено: {property_obj.title}")
        
        logger.info("🔧 Инициализация процессора панорам...")
        processor = PanoramaProcessor()
        
        if property_obj.tour_360_file_id:
            logger.info(f"🗑️ Удаление существующих файлов панорамы: {property_obj.tour_360_file_id}")
            try:
                await processor.delete_panorama_files(property_obj.tour_360_file_id, property_id)
                logger.info("✅ Существующие файлы панорамы удалены")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка удаления существующих файлов: {str(e)}")
        
        logger.info("🎨 Начинаем обработку панорамы...")
        result = await processor.upload_panorama(file, property_id)
        logger.info("🎉 Панорама успешно обработана!")
        
        if not result.get("success"):
            error_message = result.get("message", "Неизвестная ошибка при загрузке панорамы")
            logger.error(f"❌ Ошибка загрузки панорамы: {error_message}")
            raise HTTPException(status_code=500, detail=f"Ошибка загрузки панорамы: {error_message}")
        
        logger.info("💾 Сохранение данных в базу данных...")
        property_obj.tour_360_file_id = result['file_id']
        property_obj.tour_360_original_url = result['urls']['original']
        property_obj.tour_360_optimized_url = result['urls']['optimized']
        property_obj.tour_360_preview_url = result['urls']['preview']
        property_obj.tour_360_thumbnail_url = result['urls']['thumbnail']
        property_obj.tour_360_metadata = json.dumps(result['metadata'], ensure_ascii=False)
        property_obj.tour_360_uploaded_at = datetime.now()
        
        property_obj.tour_360_url = None
        
        logger.debug("🔄 Выполнение коммита в базе данных...")
        db.commit()
        logger.info("✅ Данные успешно сохранены в базе данных")
        
        logger.debug("🔄 Обновление объекта из БД...")
        db.refresh(property_obj)
        
        response_data = {
            "success": True,
            "message": "360° панорама успешно загружена и обработана",
            "file_id": result['file_id'],
            "urls": {
                "original": result['urls']['original'],
                "optimized": result['urls']['optimized'],
                "preview": result['urls']['preview'],
                "thumbnail": result['urls']['thumbnail']
            },
            "metadata": result['metadata'],
            "uploaded_at": datetime.now().isoformat()
        }
        
        logger.info("🎉 Загрузка 360° панорамы завершена успешно!")
        logger.debug(f"📋 Ответ клиенту: {json.dumps(response_data, indent=2, ensure_ascii=False, default=str)}")
        
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Критическая ошибка при загрузке панорамы: {str(e)}")
        logger.exception("Полный стек ошибки:")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки панорамы: {str(e)}")

@router.delete("/companies/properties/{property_id}/360")
async def delete_company_panorama(
    property_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    """Удаление 360° панорамы для компаний"""
    logger.info(f"🗑️ Удаление 360° панорамы для свойства {property_id} (компания)")
    
    # Проверка доступа компании
    company = await check_company_access(request, db)
    if isinstance(company, RedirectResponse):
        return company
    
    try:
        # Получение объявления
        logger.debug(f"🔍 Поиск объявления с ID: {property_id}")
        property_obj = db.query(models.Property).filter(
            models.Property.id == property_id,
            models.Property.owner_id == company.id
        ).first()
        
        if not property_obj:
            logger.error(f"❌ Объявление с ID {property_id} не найдено или не принадлежит компании")
            raise HTTPException(status_code=404, detail="Объявление не найдено")
        
        logger.info(f"✅ Объявление найдено: {property_obj.title}")
        
        # Удаление файлов если они есть
        if property_obj.tour_360_file_id:
            logger.info(f"🗑️ Удаление файлов панорамы: {property_obj.tour_360_file_id}")
            processor = PanoramaProcessor()
            try:
                await processor.delete_panorama_files(property_obj.tour_360_file_id, property_id)
                logger.info("✅ Файлы панорамы удалены")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка удаления файлов: {str(e)}")
        
        # Очистка полей в базе данных
        logger.info("🧹 Очистка полей панорамы в базе данных...")
        property_obj.tour_360_url = None
        property_obj.tour_360_file_id = None
        property_obj.tour_360_original_url = None
        property_obj.tour_360_optimized_url = None
        property_obj.tour_360_preview_url = None
        property_obj.tour_360_thumbnail_url = None
        property_obj.tour_360_metadata = None
        property_obj.tour_360_uploaded_at = None
        
        db.commit()
        logger.info("✅ Панорама успешно удалена из базы данных")
        
        return JSONResponse(content={
            "success": True,
            "message": "360° панорама успешно удалена"
        })
        
    except Exception as e:
        logger.error(f"💥 Ошибка удаления панорамы: {str(e)}")
        logger.exception("Полный стек ошибки:")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления панорамы: {str(e)}") 