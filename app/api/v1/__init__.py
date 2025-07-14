from fastapi import APIRouter

from app.api.v1 import users, auth, properties, messages, support, requests, push, chat, chat_contacts, weather, currency

api_router = APIRouter()
api_router.include_router(auth.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(properties.router, prefix="/properties", tags=["properties"])
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
api_router.include_router(support.router, prefix="/support", tags=["support"])
api_router.include_router(requests.router, prefix="/requests", tags=["requests"])
api_router.include_router(push.router, prefix="/push", tags=["push"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(chat_contacts.router, prefix="/contacts", tags=["contacts"])
api_router.include_router(weather.router, prefix="/weather", tags=["weather"])
api_router.include_router(currency.router, prefix="/currency", tags=["currency"])

# You can add other routers from this directory here
# For example: 
# from .users import router as users_router
# from .properties import router as properties_router
# api_router.include_router(users_router, prefix="/users", tags=["users"])
# api_router.include_router(properties_router, prefix="/properties", tags=["properties"]) 