import uuid
import os
import shutil
import io
from typing import List, Optional, Dict, Any
from fastapi import UploadFile
from pathlib import Path
from PIL import Image, ImageOps
from datetime import datetime
import aiofiles

class MediaUploader:
    def __init__(self, media_path: str = "media"):
        self.media_path = Path(media_path)
        self.media_path.mkdir(exist_ok=True)
        
    def generate_property_id(self) -> str:
        hex_chars = f"{uuid.uuid4().hex}"
        return f"{hex_chars[0:4]}-{hex_chars[4:8]}-{hex_chars[8:12]}-{hex_chars[12:16]}"
    
    async def ping_server(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "data": {"message": "Local media server ready"},
            "connected": True
        }
    
    def _resize_image(self, image: Image.Image, size: tuple, quality: int = 85) -> bytes:
        image = ImageOps.exif_transpose(image)
        image.thumbnail(size, Image.Resampling.LANCZOS)
        
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=quality, optimize=True)
        return buffer.getvalue()
    
    async def _save_image_variants(self, image: Image.Image, base_path: Path, file_id: str) -> Dict[str, str]:
        variants = {
            'original': (4096, 4096, 95),
            'large': (1920, 1080, 85),
            'medium': (800, 600, 80),
            'small': (400, 300, 75),
            'thumbnail': (150, 150, 70)
        }
        
        urls = {}
        for variant, (width, height, quality) in variants.items():
            variant_data = self._resize_image(image.copy(), (width, height), quality)
            variant_path = base_path / f"{file_id}_{variant}.jpg"
            
            async with aiofiles.open(variant_path, 'wb') as f:
                await f.write(variant_data)
            
            relative_path = base_path.relative_to(self.media_path)
            relative_path_str = str(relative_path).replace("\\", "/")
            urls[variant] = f"/media/{relative_path_str}/{file_id}_{variant}.jpg"
        
        return urls
    
    async def upload_panorama(self, file_input, property_id: str) -> Dict[str, Any]:
        try:
            if hasattr(file_input, 'read'):
                file_content = await file_input.read()
                filename = file_input.filename
            elif isinstance(file_input, dict) and 'content' in file_input:
                file_content = file_input['content']
                filename = file_input.get('filename', 'panorama.jpg')
            else:
                file_content = file_input
                filename = "panorama.jpg"
            
            file_id = str(uuid.uuid4())
            
            panorama_dir = self.media_path / "panoramas" / property_id
            panorama_dir.mkdir(parents=True, exist_ok=True)
            
            image = Image.open(io.BytesIO(file_content))
            
            if image.width < 2048 or image.height < 1024:
                return {
                    "status": "error",
                    "message": "Panorama must be at least 2048x1024 pixels"
                }
            
            urls = await self._save_image_variants(image, panorama_dir, file_id)
            
            return {
                "status": "success",
                "file_id": file_id,
                "original_url": urls.get("original", ""),
                "optimized_url": urls.get("large", ""),
                "preview_url": urls.get("medium", ""),
                "thumbnail_url": urls.get("thumbnail", ""),
                "uploaded_at": datetime.now(),
                "metadata": {
                    "original_name": filename,
                    "file_size": len(file_content),
                    "dimensions": f"{image.width}x{image.height}"
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Panorama upload error: {str(e)}"
            }
        finally:
            if hasattr(file_input, 'seek'):
                await file_input.seek(0)

    async def upload_property_images(self, files: List[UploadFile], property_id: Optional[str] = None) -> Dict[str, Any]:
        if not property_id:
            property_id = self.generate_property_id()
        
        if not files:
            return {
                "status": "error",
                "message": "No files provided"
            }
        
        try:
            images_dir = self.media_path / "properties" / property_id
            images_dir.mkdir(parents=True, exist_ok=True)
            
            uploaded_files = []
            
            for file in files:
                file_content = await file.read()
                file_id = str(uuid.uuid4())
                
                image = Image.open(io.BytesIO(file_content))
                urls = await self._save_image_variants(image, images_dir, file_id)
                
                uploaded_files.append({
                    'file_id': file_id,
                    'filename': f"{file_id}.jpg",
                    'original_name': file.filename,
                    'urls': urls,
                    'url': urls.get('large', '')
                })
                
                await file.seek(0)
            
            return {
                "status": "success",
                "property_id": property_id,
                "files": uploaded_files,
                "count": len(uploaded_files),
                "message": "Upload successful"
            }
                    
        except Exception as e:
            return {
                "status": "error",
                "message": f"Upload error: {str(e)}"
            }
    
    async def delete_property_images(self, property_id: str) -> Dict[str, Any]:
        try:
            property_dir = self.media_path / "properties" / property_id
            if property_dir.exists():
                shutil.rmtree(property_dir)
            
            panorama_dir = self.media_path / "panoramas" / property_id
            if panorama_dir.exists():
                shutil.rmtree(panorama_dir)
            
            return {
                "status": "success",
                "message": "Images deleted successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Delete error: {str(e)}"
            }
    
    async def upload_file(self, file: UploadFile, folder: str = "service_cards") -> Dict[str, Any]:
        try:
            file_content = await file.read()
            file_id = str(uuid.uuid4())
            
            upload_dir = self.media_path / folder
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
            filename = f"{file_id}.{file_extension}"
            file_path = upload_dir / filename
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            
            return {
                "status": "success",
                "file_id": file_id,
                "filename": filename,
                "url": f"/media/{folder}/{filename}",
                "message": "File uploaded successfully"
            }
                    
        except Exception as e:
            return {
                "status": "error",
                "message": f"Upload error: {str(e)}"
            }

media_uploader = MediaUploader() 