from fastapi import WebSocket
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models.chat import AppChatModel, AppChatMessageModel
from datetime import datetime
import json


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.chat_messages: Dict[str, List[dict]] = {}
        
        # Загружаем сохраненные сообщения при запуске
        self.load_messages_from_file()
        
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)
    
    async def broadcast(self, message: dict, exclude: WebSocket = None):
        # Получаем ID получателя
        receiver_id = str(message.get("receiver_id"))
        
        # Если это сообщение чата, сохраняем его в памяти
        if message.get("type") in ["message_sent", "new_message"] and "message" in message:
            # Получаем sender_id и receiver_id из сообщения
            sender_id = message["message"].get("sender_id")
            receiver_id = message["message"].get("receiver_id")
            
            if sender_id and receiver_id:
                # Формируем уникальный chat_id для пары пользователей (всегда используем меньший ID первым)
                chat_id = self.get_chat_id(sender_id, receiver_id)
                self.add_message_to_memory(chat_id, message["message"])
            else:
                print(f"ERROR: Не удалось определить sender_id или receiver_id в сообщении: {message}")
        
        # Отправляем сообщение всем соединениям получателя
        for connection in self.active_connections.get(receiver_id, []):
            if connection != exclude:
                await connection.send_json(message)
    
    def is_user_online(self, user_id: str) -> bool:
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
        
    def get_chat_id(self, user1_id, user2_id) -> str:
        """Формирует уникальный идентификатор чата для пары пользователей"""
        # Преобразуем в целые числа, если они еще не являются целыми
        try:
            user1_id = int(user1_id)
            user2_id = int(user2_id)
        except (ValueError, TypeError):
            # Если не удалось преобразовать в числа, используем строки
            user1_id = str(user1_id)
            user2_id = str(user2_id)
        
        # Всегда используем меньший ID первым для создания уникального идентификатора
        if user1_id > user2_id:
            user1_id, user2_id = user2_id, user1_id
        
        # Формируем уникальный идентификатор чата в формате "user1_id-user2_id"
        return f"{user1_id}-{user2_id}"
    
    async def save_message_to_db(self, message_data: dict, db: Session):
        try:
            sender_id = message_data["sender_id"]
            receiver_id = message_data["receiver_id"]
            content = message_data["content"]
            
            # Находим или создаем чат между отправителем и получателем
            chat = db.query(AppChatModel).filter(
                or_(
                    and_(AppChatModel.user1_id == sender_id, AppChatModel.user2_id == receiver_id),
                    and_(AppChatModel.user1_id == receiver_id, AppChatModel.user2_id == sender_id)
                )
            ).first()
            
            if not chat:
                # Создаем новый чат
                chat = AppChatModel(
                    user1_id=sender_id,
                    user2_id=receiver_id
                )
                db.add(chat)
                db.commit()
                db.refresh(chat)
            
            # Создаем новое сообщение
            current_time = datetime.now()
            db_message = AppChatMessageModel(
                chat_id=chat.id,
                sender_id=sender_id,
                content=content,
                is_read=False,
                created_at=current_time  # Явно задаем время создания
            )
            
            db.add(db_message)
            db.commit()
            db.refresh(db_message)
            
            # Проверяем, что created_at не None
            timestamp = current_time.isoformat() if db_message.created_at is None else db_message.created_at.isoformat()
            
            # Возвращаем сообщение в формате JSON
            return {
                "id": db_message.id,
                "chat_id": db_message.chat_id,
                "sender_id": db_message.sender_id,
                "receiver_id": receiver_id,  # Добавляем receiver_id для удобства
                "content": db_message.content,
                "timestamp": timestamp,
                "is_read": db_message.is_read
            }
        except Exception as e:
            print(f"ERROR: Ошибка при сохранении сообщения в базу данных: {e}")
            
            # В случае ошибки создаем временное сообщение без сохранения в базу
            from uuid import uuid4
            
            current_time = datetime.now()
            # Используем метод get_chat_id для создания уникального идентификатора чата
            chat_id = self.get_chat_id(sender_id, receiver_id)
            
            temp_message = {
                "id": str(uuid4()),
                "chat_id": chat_id,
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "content": content,
                "timestamp": current_time.isoformat(),
                "is_read": False,
                "is_temporary": True  # Добавляем флаг, что это временное сообщение
            }
            return temp_message
    
    def load_messages_from_file(self):
        """Загружает сообщения из JSON-файла"""
        try:
            import os
            import json
            
            if os.path.exists("chat_messages.json"):
                with open("chat_messages.json", "r", encoding="utf-8") as f:
                    data = f.read()
                    if data.strip():  # проверяем, что файл не пустой
                        self.chat_messages = json.loads(data)
                        print(f"DEBUG: Загружены сохраненные сообщения чатов. Доступные комнаты: {list(self.chat_messages.keys())}")
                        for room, messages in self.chat_messages.items():
                            print(f"DEBUG: Комната {room}: {len(messages)} сообщений")
                            # Выводим первое и последнее сообщение для отладки
                            if messages:
                                print(f"DEBUG: Первое сообщение: {messages[0].get('content', 'Нет контента')}")
                                if len(messages) > 1:
                                    print(f"DEBUG: Последнее сообщение: {messages[-1].get('content', 'Нет контента')}")
            else:
                print("DEBUG: Файл с сообщениями не найден")
        except Exception as e:
            print(f"ERROR: Ошибка при загрузке сообщений из файла: {e}")
            self.chat_messages = {}
    
    def save_messages_to_file(self):
        """Сохраняет сообщения в JSON-файл"""
        try:
            import json
            with open("chat_messages.json", "w", encoding="utf-8") as f:
                json.dump(self.chat_messages, f, ensure_ascii=False, indent=2)
            print(f"DEBUG: Сообщения сохранены в файл. Всего комнат: {len(self.chat_messages)}")
        except Exception as e:
            print(f"ERROR: Ошибка при сохранении сообщений в файл: {e}")
    
    def add_message_to_memory(self, chat_id: str, message: dict):
        """Добавляет сообщение в память и сохраняет в файл"""
        if chat_id not in self.chat_messages:
            self.chat_messages[chat_id] = []
        
        # Проверяем, есть ли уже сообщение с таким ID
        for existing_msg in self.chat_messages[chat_id]:
            if existing_msg.get("id") == message.get("id"):
                print(f"DEBUG: Сообщение с ID {message.get('id')} уже существует, пропускаем")
                return
        
        # Добавляем сообщение в память
        self.chat_messages[chat_id].append(message)
        print(f"DEBUG: Добавлено сообщение в комнату {chat_id}: {message.get('content')}")
        
        # Сохраняем в файл после добавления нового сообщения
        self.save_messages_to_file()


manager = ConnectionManager()
