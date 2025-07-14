import os
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Путь к заглушке для изображений
DEFAULT_IMAGE = "/static/layout/assets/img/property-placeholder.jpg"

def get_valid_image_url(url):
    """
    Проверяет наличие изображения по указанному URL
    Если изображение не найдено, возвращает заглушку
    """
    if not url:
        return DEFAULT_IMAGE
        
    # Если это абсолютный URL (начинается с http), возвращаем как есть
    if url.startswith('http'):
        return url
        
    # Получаем путь к файлу без префикса /static или /media
    file_path = None
    base_dir = Path(__file__).resolve().parent.parent.parent
    
    if url.startswith('/static/'):
        file_path = base_dir / 'static' / url[8:]
    elif url.startswith('/media/'):
        file_path = base_dir / 'media' / url[7:]
    else:
        # Если URL не начинается с /static/ или /media/, пробуем поискать в обеих директориях
        static_path = base_dir / 'static' / url.lstrip('/')
        media_path = base_dir / 'media' / url.lstrip('/')
        
        if static_path.exists():
            file_path = static_path
        elif media_path.exists():
            file_path = media_path
    
    # Проверяем существование файла
    if file_path and file_path.exists():
        return url
    
    # Возвращаем заглушку, если файл не найден
    return DEFAULT_IMAGE
