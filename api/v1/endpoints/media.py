from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.api import deps
from app.utils.media_uploader import media_uploader

router = APIRouter()

@router.get("/ping")
async def test_media_connection() -> Dict[str, Any]:
    """Проверка связи с медиа-сервером"""
    result = await media_uploader.ping_server()
    return result

@router.post("/test-upload")
async def test_media_upload(
    files: List[UploadFile] = File(...),
    property_id: str = Form(None)
) -> Dict[str, Any]:
    """Тестовая загрузка изображений"""
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Проверяем файлы
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    for file in files:
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file.content_type} not allowed"
            )
    
    # Загружаем
    result = await media_uploader.upload_property_images(files, property_id)
    
    if result["status"] != "success":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.delete("/test-delete/{property_id}")
async def test_media_delete(property_id: str) -> Dict[str, Any]:
    """Тестовое удаление изображений"""
    
    result = await media_uploader.delete_property_images(property_id)
    
    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return result

@router.get("/info")
async def media_info() -> Dict[str, Any]:
    """Информация о медиа-системе"""
    
    ping_result = await media_uploader.ping_server()
    
    return {
        "media_server": "https://wazir.kg/state",
        "connection": ping_result,
        "sample_property_id": media_uploader.generate_property_id(),
        "endpoints": {
            "upload": "https://wazir.kg/state/upload.php",
            "delete": "https://wazir.kg/state/delete.php"
        },
        "supported_formats": ["image/jpeg", "image/jpg", "image/png", "image/webp"],
        "image_sizes": {
            "original": "Оригинальный размер",
            "large": "1200x900px", 
            "medium": "800x600px",
            "thumb": "300x200px"
        },
        "folder_structure": {
            "pattern": "uploads/xxxx-xxxx-xxxx-xxxx/",
            "subfolders": ["original/", "large/", "medium/", "thumb/"]
        }
    } 