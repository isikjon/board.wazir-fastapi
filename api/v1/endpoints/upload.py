from typing import List
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
from app.api import deps
from app.models.user import User
from app.models.property import PropertyImage, Property

router = APIRouter()

# Функция для создания директории, если она не существует
def ensure_directory_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

@router.post("/images/property/")
async def upload_property_images(
    *,
    files: List[UploadFile] = File(...),
    property_id: int = Form(None),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> List[dict]:
    """
    Загрузка изображений для объявления о недвижимости.
    Возвращает список URL-адресов загруженных изображений.
    """
    print(f"DEBUG: Начало загрузки изображений, пользователь: {current_user.id}, кол-во файлов: {len(files)}")
    
    if not files:
        print("DEBUG: Файлы не предоставлены")
        raise HTTPException(status_code=400, detail="Файлы не предоставлены")
    
    # Создаем необходимые директории
    # Используем директорию static вместо media, так как к ней точно есть доступ
    media_dir = "static"
    ensure_directory_exists(media_dir)
    properties_dir = os.path.join(media_dir, "uploads")
    ensure_directory_exists(properties_dir)
    user_dir = os.path.join(properties_dir, str(current_user.id))
    ensure_directory_exists(user_dir)
    
    print(f"DEBUG: Директория для сохранения файлов: {user_dir}")
    
    # Обрабатываем загруженные файлы
    uploaded_files = []
    
    print(f"DEBUG: Начинаем обработку {len(files)} файлов")
    
    for i, file in enumerate(files):
        try:
            # Сбрасываем позицию чтения файла перед чтением
            await file.seek(0)
            
            if not file.content_type.startswith("image/"):
                print(f"DEBUG: Пропуск файла {file.filename} - не изображение")
                continue
            
            print(f"DEBUG: Обработка файла #{i+1}: {file.filename}, тип: {file.content_type}")
            
            # Генерируем уникальное имя файла
            file_extension = os.path.splitext(file.filename)[1] if "." in file.filename else ".jpg"
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(user_dir, unique_filename)
            
            # Сохраняем файл
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Формируем URL для доступа к файлу (соответствует новому пути хранения)
            file_url = f"/static/uploads/{current_user.id}/{unique_filename}"
            print(f"DEBUG: Файл сохранен: {file_path}, URL: {file_url}")
            print(f"DEBUG: Размер файла: {len(content)} байт")
            
            # Если указан property_id, создаем запись в БД
            if property_id:
                # Проверяем, есть ли у текущего пользователя доступ к этому объявлению
                property_obj = db.query(Property).filter_by(
                    id=property_id, 
                    owner_id=current_user.id
                ).first()
                
                if property_obj:
                    # Проверяем, есть ли у объявления главное изображение
                    has_main_image = db.query(PropertyImage).filter_by(
                        property_id=property_id,
                        is_main=True
                    ).first() is not None
                    
                    # Создаем запись в БД
                    image = PropertyImage(
                        url=file_url,
                        property_id=property_id,
                        is_main=not has_main_image  # Первое загруженное изображение будет главным
                    )
                    db.add(image)
                    db.commit()
                    db.refresh(image)
                    print(f"DEBUG: Изображение добавлено в БД, ID: {image.id}, is_main: {image.is_main}")
            
            # Добавляем файл в список успешно загруженных
            uploaded_files.append({
                "url": file_url,
                "filename": unique_filename,
                "size": len(content),
                "index": i  # Добавляем индекс для отладки
            })
            print(f"DEBUG: Добавлен файл в список загрузок: {file_url}")
        except Exception as e:
            print(f"ERROR: Ошибка при обработке файла {file.filename}: {str(e)}")
    
    if not uploaded_files:
        print("DEBUG: Не удалось загрузить ни одного изображения")
        raise HTTPException(status_code=400, detail="Не удалось загрузить изображения")
    
    print(f"DEBUG: Успешно загружено {len(uploaded_files)} изображений")
    print(f"DEBUG: Список URL: {[f['url'] for f in uploaded_files]}")
    return uploaded_files
