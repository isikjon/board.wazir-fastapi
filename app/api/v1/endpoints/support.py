from typing import Any, List, Optional
from datetime import datetime, timedelta
import random

from fastapi import APIRouter, Depends, HTTPException, Form, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app import deps
from app.models.user import User
from app.models.support import SupportTicket, SupportMessage
from app.schemas.support import SupportTicketCreate, SupportMessageCreate, SupportTicketResponse, SupportMessageResponse
from app.models.chat import AppChatModel

router = APIRouter()

# Вспомогательная функция для форматирования datetime в строку
def format_datetime(dt):
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return dt

# Функция для получения списка тикетов поддержки
def get_support_tickets():
    # В реальном приложении здесь будет запрос к базе данных
    tickets = []
    
    # Генерируем случайные тикеты для демонстрации
    statuses = ["new", "active", "waiting", "closed"]
    for i in range(1, 11):
        status = random.choice(statuses)
        
        status_class_map = {
            "new": "status-new",
            "active": "status-active",
            "waiting": "status-waiting",
            "closed": "status-closed"
        }
        
        status_display_map = {
            "new": "Новый",
            "active": "Активный",
            "waiting": "Ожидает",
            "closed": "Закрыт"
        }
        
        # Создаем случайное время последнего сообщения
        hours_ago = random.randint(0, 72)
        last_message_time = datetime.now() - timedelta(hours=hours_ago)
        
        # Форматируем время в зависимости от того, насколько оно старое
        if hours_ago < 24:
            time_display = last_message_time.strftime("%H:%M")
        else:
            days = hours_ago // 24
            if days == 1:
                time_display = "Вчера"
            else:
                time_display = f"{days} дн. назад"
        
        ticket = {
            "id": 4580 + i,
            "user": {
                "id": 100230 + i,
                "full_name": f"Пользователь {i}",
                "phone": f"+7 (9{random.randint(10, 99)}) {random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10, 99)}"
            },
            "subject": random.choice([
                "Проблема с размещением объявления", 
                "Не могу войти в аккаунт", 
                "Как добавить фотографии?", 
                "Вопрос по оплате", 
                "Не отображается 360-тур"
            ]),
            "status": status,
            "status_class": status_class_map[status],
            "status_display": status_display_map[status],
            "last_message_time": time_display,
            "last_message_preview": random.choice([
                "Здравствуйте! Помогите пожалуйста разобраться...",
                "Спасибо за оперативный ответ, но у меня возник...",
                "Я уже несколько раз пытался...",
                "А можно как-то ускорить процесс?",
                "Так и не получается решить проблему..."
            ])
        }
        
        tickets.append(ticket)
    
    return tickets

# Функция для получения подробной информации о тикете
def get_ticket_details(ticket_id):
    # В реальном приложении здесь будет запрос к базе данных
    
    # Найдем тикет в списке
    tickets = get_support_tickets()
    ticket = next((t for t in tickets if str(t["id"]) == str(ticket_id)), None)
    
    if not ticket:
        return None
    
    # Добавляем дополнительную информацию
    ticket["messages_count"] = random.randint(3, 15)
    
    return ticket

# Функция для получения сообщений тикета
def get_ticket_messages(ticket_id):
    # В реальном приложении здесь будет запрос к базе данных
    
    # Проверим, что тикет существует
    ticket = get_ticket_details(ticket_id)
    if not ticket:
        return {}
    
    # Генерируем случайные сообщения
    messages_count = ticket["messages_count"]
    
    # Сообщения, сгруппированные по датам
    messages_by_date = {}
    
    # Генерируем даты за последние несколько дней
    today = datetime.now().date()
    
    # Определяем возможные даты (сегодня, вчера, несколько дней назад)
    dates = [today - timedelta(days=d) for d in range(min(messages_count // 2, 5))]
    
    # Форматируем даты для отображения
    date_formats = {}
    for d in dates:
        if d == today:
            date_formats[d] = "Сегодня"
        elif d == today - timedelta(days=1):
            date_formats[d] = "Вчера"
        else:
            date_formats[d] = d.strftime("%d.%m.%Y")
    
    # Распределяем сообщения по датам
    messages = []
    for i in range(messages_count):
        msg_date = random.choice(dates)
        msg_time = datetime.combine(
            msg_date, 
            datetime.min.time()
        ) + timedelta(hours=random.randint(9, 21), minutes=random.randint(0, 59))
        
        # Определяем, от кого сообщение (пользователь/админ)
        is_admin = bool(i % 2)  # Чередуем отправителей
        
        message = {
            "id": i + 1,
            "content": random.choice([
                "Здравствуйте! Чем я могу вам помочь?",
                "У меня возникла проблема с размещением объявления.",
                "Пожалуйста, опишите подробнее, что именно не получается.",
                "При загрузке фотографий возникает ошибка.",
                "Спасибо за обращение. Мы рассмотрим вашу проблему в ближайшее время.",
                "Когда примерно ожидать ответа?",
                "Обычно мы отвечаем в течение 24 часов.",
                "Проблема решена! Благодарю за помощь.",
                "Рад был помочь. Если возникнут еще вопросы, обращайтесь."
            ]),
            "is_admin": is_admin,
            "admin_id": f"ID-{random.randint(1, 10)}" if is_admin else None,
            "is_read": True if msg_date < today else random.choice([True, False]),
            "time": msg_time.strftime("%H:%M"),
            "created_at": format_datetime(msg_time)
        }
        
        date_key = date_formats[msg_date]
        if date_key not in messages_by_date:
            messages_by_date[date_key] = []
        
        messages_by_date[date_key].append(message)
    
    # Сортируем сообщения внутри каждой даты по времени
    for date_key in messages_by_date:
        messages_by_date[date_key].sort(key=lambda m: m["time"])
    
    return messages_by_date

# Функция для получения новых сообщений
def get_new_ticket_messages(ticket_id, last_message_id):
    # В реальном приложении здесь будет запрос к базе данных
    # для получения новых сообщений после указанного ID
    
    # Симулируем отсутствие новых сообщений в 90% случаев
    if random.random() > 0.1:
        return []
    
    # Симулируем 1-3 новых сообщения
    num_messages = random.randint(1, 3)
    messages = []
    
    for i in range(num_messages):
        # Увеличиваем ID сообщения
        message_id = last_message_id + i + 1
        
        # Определяем случайно, от кого сообщение
        is_admin = random.choice([True, False])
        
        # Создаем случайное сообщение
        content = random.choice([
            "Здравствуйте! Чем я могу вам помочь?",
            "Спасибо за информацию, я проверю это.",
            "Мы решим вашу проблему в ближайшее время.",
            "Можете предоставить больше деталей?",
            "Я уточню эту информацию у технического отдела.",
            "Ваш запрос был передан соответствующему отделу.",
            "Проблема решена. Спасибо за ваше терпение!"
        ])
        
        # Симулируем время создания сообщения
        created_at = datetime.now() - timedelta(minutes=random.randint(1, 30))
        time_str = created_at.strftime("%H:%M")
        
        # Cоздаем объект сообщения
        message = {
            "id": message_id,
            "content": content,
            "is_admin": is_admin,
            "admin_id": "Admin-" + str(random.randint(1, 5)) if is_admin else None,
            "is_read": random.choice([True, False]),
            "time": time_str,
            "created_at": format_datetime(created_at)
        }
        
        messages.append(message)
    
    return messages

# Функция для сохранения сообщения
def save_support_message(ticket_id, content, admin_id):
    # В реальном приложении здесь будет сохранение в базу данных
    # и возврат реального ID созданного сообщения
    
    # Для демонстрации просто возвращаем случайный ID
    return random.randint(1000, 9999)

# Функция для закрытия тикета
def close_support_ticket(ticket_id):
    # В реальном приложении здесь будет обновление статуса в базе данных
    
    # Для демонстрации просто возвращаем успех
    return True

@router.get("/tickets", response_model=List[SupportTicketResponse])
def get_support_tickets(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    status: Optional[str] = None,
    skip: int = 0, 
    limit: int = 100
) -> Any:
    """
    Получение списка тикетов поддержки.
    """
    # Обычные пользователи видят только свои тикеты
    if not current_user.is_admin:
        query = db.query(SupportTicket).filter(SupportTicket.user_id == current_user.id)
    else:
        query = db.query(SupportTicket)
    
    if status:
        query = query.filter(SupportTicket.status == status)
    
    tickets = query.order_by(SupportTicket.updated_at.desc()).offset(skip).limit(limit).all()
    
    return tickets

@router.post("/tickets", response_model=SupportTicketResponse)
def create_support_ticket(
    ticket_data: SupportTicketCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Создание нового тикета поддержки.
    """
    try:
        # Создаем чат между пользователем и администратором (ID=3 по умолчанию)
        admin_id = 3  # Фиксированный ID администратора для демонстрации
        
        # Ищем существующий чат между пользователем и админом
        existing_chat = db.query(AppChatModel).filter(
            ((AppChatModel.user1_id == current_user.id) & (AppChatModel.user2_id == admin_id)) |
            ((AppChatModel.user1_id == admin_id) & (AppChatModel.user2_id == current_user.id))
        ).first()
        
        if existing_chat:
            chat_id = existing_chat.id
            print(f"DEBUG: Найден существующий чат между пользователем {current_user.id} и админом {admin_id}, ID чата: {chat_id}")
        else:
            # Создаем новый чат
            print(f"DEBUG: Создание нового чата между пользователем {current_user.id} и админом {admin_id}")
            new_chat = AppChatModel(
                user1_id=current_user.id,
                user2_id=admin_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(new_chat)
            db.commit()
            db.refresh(new_chat)
            chat_id = new_chat.id
        
        # Создаем тикет и связываем его с чатом
        ticket = SupportTicket(
            user_id=current_user.id,
            subject=ticket_data.subject,
            description=ticket_data.description,
            status="OPEN",
            chat_id=chat_id  # Важно: устанавливаем ID чата в тикете
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        print(f"DEBUG: Тикет создан успешно, ID: {ticket.id}")
        
        # Также создаем первое сообщение в чате с описанием тикета
        print(f"DEBUG: Создание сообщения в чат {chat_id} с описанием тикета")
        if ticket_data.message:
            message_content = ticket_data.message
        elif ticket_data.description:
            message_content = ticket_data.description
        else:
            message_content = f"Запрос в поддержку: {ticket_data.subject}"
            
        support_message = SupportMessage(
            ticket_id=ticket.id,
            content=message_content,
            is_admin=False,
            user_id=current_user.id,
            is_read=False
        )
        db.add(support_message)
        db.commit()
        db.refresh(support_message)
        print(f"DEBUG: Сообщение создано, ID чата: {chat_id}")
        
        return ticket
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Ошибка при создании тикета: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании тикета: {str(e)}"
        )

@router.get("/tickets/{ticket_id}", response_model=SupportTicketResponse)
def get_support_ticket(
    ticket_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Получение информации о конкретном тикете.
    """
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    
    # Проверка доступа: администраторы видят все тикеты, пользователи - только свои
    if not current_user.is_admin and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому тикету")
    
    return ticket

@router.post("/message", response_model=SupportMessageResponse)
def send_support_message(
    ticket_id: int = Form(...),
    content: str = Form(...),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Отправка сообщения в тикет поддержки.
    """
    # Проверяем существование тикета
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тикет не найден"
        )
    
    # Проверяем, не закрыт ли тикет
    if ticket.status == "CLOSED" or ticket.status == "closed" or ticket.status == TicketStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Тикет закрыт"
        )
    
    # Получаем chat_id из тикета
    chat_id = ticket.chat_id
    
    # Проверяем права доступа (админ или владелец тикета)
    is_admin = hasattr(current_user, "role") and current_user.role == "ADMIN"
    if not is_admin and ticket.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому тикету"
        )
    
    # Если это первое сообщение от администратора, меняем статус на "в процессе"
    if is_admin and ticket.status == "OPEN" or ticket.status == TicketStatus.OPEN:
        ticket.status = TicketStatus.IN_PROGRESS
        print(f"DEBUG: Статус тикета {ticket_id} изменен на IN_PROGRESS")
    
    # Создаем сообщение
    message = SupportMessage(
        ticket_id=ticket_id,
        content=content,
        is_admin=is_admin,
        admin_id=current_user.id if is_admin else None,
        user_id=None if is_admin else current_user.id,
        is_read=False
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    print(f"DEBUG: Сообщение {message.id} успешно сохранено в тикет {ticket_id}")
    
    # Отправляем сообщение в WebSocket, если доступно
    try:
        # Импортируем ConnectionManager из main
        from main import manager
        
        # Формируем данные сообщения
        message_data = {
            "type": "new_message",
            "chat_id": chat_id if chat_id else ticket_id,
            "ticket_id": ticket_id,
            "message_id": message.id,
            "sender_id": current_user.id,
            "content": message.content,
            "is_read": message.is_read,
            "is_admin": message.is_admin,
            "created_at": message.created_at.isoformat() if message.created_at else None,
            "time": message.created_at.strftime("%H:%M") if message.created_at else datetime.now().strftime("%H:%M")
        }
        
        # Рассылаем в обе комнаты - и по chat_id, и по ticket_id
        if chat_id and chat_id != ticket_id:
            chat_room = f"chat_{chat_id}"
            print(f"DEBUG: Сохранено сообщение в комнату {chat_room}, всего сообщений: {len(manager.get_messages(chat_room)) + 1}")
            manager.save_message(chat_room, message_data)
            manager.broadcast(message_data, chat_room)
        
        # Всегда отправляем в комнату тикета
        ticket_room = f"chat_{ticket_id}"
        manager.broadcast(message_data, ticket_room)
        
    except Exception as e:
        print(f"DEBUG: Ошибка отправки в WebSocket: {str(e)}")
    
    return message

@router.get("/tickets/{ticket_id}/messages", response_model=List[SupportMessageResponse])
def get_ticket_messages(
    ticket_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """
    Получение сообщений тикета поддержки.
    """
    # Проверяем существование тикета
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тикет не найден"
        )
    
    # Проверяем права доступа (админ или владелец тикета)
    is_admin = hasattr(current_user, "role") and current_user.role == "ADMIN"
    if not is_admin and ticket.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому тикету"
        )
    
    # Получаем сообщения
    messages = db.query(SupportMessage).filter(
        SupportMessage.ticket_id == ticket_id
    ).order_by(SupportMessage.created_at.asc()).offset(skip).limit(limit).all()
    
    # Отмечаем сообщения как прочитанные
    # Для админа отмечаем сообщения от пользователя, для пользователя - от админа
    for message in messages:
        if (is_admin and not message.is_admin and not message.is_read) or \
           (not is_admin and message.is_admin and not message.is_read):
            message.is_read = True
    
    db.commit()
    
    print(f"DEBUG: Запрос на получение сообщений тикета {ticket_id} пользователем {current_user.id}")
    print(f"DEBUG: Найдено {len(messages)} сообщений для тикета {ticket_id}")
    
    # Добавляем chat_id к ответу
    result = []
    for msg in messages:
        msg_dict = {
            "id": msg.id,
            "ticket_id": msg.ticket_id,
            "chat_id": ticket.chat_id,  # Добавляем chat_id из тикета
            "content": msg.content,
            "is_admin": msg.is_admin,
            "admin_id": msg.admin_id,
            "is_read": msg.is_read,
            "time": msg.created_at.strftime("%H:%M") if msg.created_at else "00:00",
            "created_at": msg.created_at
        }
        result.append(SupportMessageResponse(**msg_dict))
    
    return result

@router.get("/tickets/{ticket_id}/messages/new", response_model=List[SupportMessageResponse])
def get_new_ticket_messages(
    ticket_id: int,
    last_id: int = Query(0),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Получение новых сообщений после last_id.
    """
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    
    # Проверка доступа
    if not current_user.is_admin and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому тикету")
    
    messages = db.query(SupportMessage)\
        .filter(SupportMessage.ticket_id == ticket_id)\
        .filter(SupportMessage.id > last_id)\
        .order_by(SupportMessage.created_at)\
        .all()
    
    # Отмечаем новые сообщения как прочитанные
    if current_user.is_admin:
        for msg in messages:
            if not msg.is_admin and not msg.is_read:
                msg.is_read = True
    else:
        for msg in messages:
            if msg.is_admin and not msg.is_read:
                msg.is_read = True
    
    db.commit()
    
    return messages

@router.put("/tickets/{ticket_id}/close")
def close_support_ticket(
    ticket_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Закрытие тикета поддержки.
    """
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    
    # Проверка доступа: только администраторы могут закрывать тикеты
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут закрывать тикеты")
    
    ticket.status = "closed"
    ticket.updated_at = datetime.now()
    
    # Добавляем системное сообщение о закрытии тикета
    message = SupportMessage(
        ticket_id=ticket_id,
        content="Тикет закрыт администратором",
        is_admin=True,
        admin_id=current_user.id,
        is_read=False
    )
    db.add(message)
    
    db.commit()
    
    return {"success": True} 