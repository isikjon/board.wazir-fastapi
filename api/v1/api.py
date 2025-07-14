from fastapi import APIRouter
from api.v1.endpoints import auth, contacts, weather, currency, chat, properties, favorites, upload, health, panorama_upload, media, telegram_auth, categories

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
api_router.include_router(weather.router, prefix="/weather", tags=["weather"])
api_router.include_router(currency.router, prefix="/currency", tags=["currency"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(properties.router, prefix="/properties", tags=["properties"])
api_router.include_router(favorites.router, prefix="/favorites", tags=["favorites"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(panorama_upload.router, prefix="/panorama_upload", tags=["panorama_upload"])
api_router.include_router(media.router, prefix="/media", tags=["media"])
api_router.include_router(telegram_auth.router, prefix="/telegram", tags=["telegram_auth"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])