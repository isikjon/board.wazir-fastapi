from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas, services
from app.api import deps
from app.models.chat import AppChatModel, AppChatMessageModel

router = APIRouter()


@router.get("/tickets", response_model=List[schemas.Ticket])
def read_tickets(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    if services.user.is_admin(current_user):
        tickets = services.ticket.get_multi(db=db, skip=skip, limit=limit)
    else:
        tickets = services.ticket.get_user_tickets(
            db=db, user_id=current_user.id, skip=skip, limit=limit
        )
    return tickets


@router.post("/tickets", response_model=schemas.Ticket)
def create_ticket(
    *,
    db: Session = Depends(deps.get_db),
    ticket_in: schemas.TicketCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    print("DEBUG: create_ticket called")
    print(f"DEBUG: ticket_in={ticket_in}")
    print(f"DEBUG: current_user.id={current_user.id}, current_user.role={getattr(current_user, 'role', None)}")
    
    # Создаем тикет
    ticket = services.ticket.create_with_user(
        db=db, obj_in=ticket_in, user_id=current_user.id
    )
    print(f"DEBUG: Создан тикет {ticket.id} для пользователя {current_user.id}")
    
    # Ищем админа
    try:
        admin = db.query(models.User).filter(models.User.role == models.UserRole.ADMIN).first()
        print(f"DEBUG: Найден админ: {admin.id if admin else None}")
    except Exception as e:
        print(f"ERROR: Ошибка при поиске админа: {e}")
        admin = None
    
    if admin:
        try:
            # Ищем существующий чат
            existing_chat = db.query(AppChatModel).filter(
                ((AppChatModel.user1_id == current_user.id) & (AppChatModel.user2_id == admin.id)) |
                ((AppChatModel.user1_id == admin.id) & (AppChatModel.user2_id == current_user.id))
            ).first()
            print(f"DEBUG: existing_chat={existing_chat.id if existing_chat else None}")
            
            if not existing_chat:
                # Создаем новый чат
                chat = AppChatModel(user1_id=current_user.id, user2_id=admin.id)
                db.add(chat)
                db.commit()
                print(f"DEBUG: Создан чат {chat.id} между {current_user.id} и {admin.id}")
            else:
                chat = existing_chat
                print(f"DEBUG: Используем существующий чат {chat.id}")
            
            # Создаем первое сообщение в чате
            if ticket_in.description:
                first_msg = AppChatMessageModel(
                    chat_id=chat.id,
                    sender_id=current_user.id,
                    content=ticket_in.description,
                    is_read=False
                )
                db.add(first_msg)
                db.commit()
                print(f"DEBUG: Создано первое сообщение {first_msg.id} в чате {chat.id}")
            else:
                print("DEBUG: Нет описания для первого сообщения")
                
        except Exception as e:
            print(f"ERROR: Ошибка при работе с чатом: {e}")
            db.rollback()
    else:
        print("ERROR: Не найден админ для создания чата!")
    
    # --- Создание чата и первого сообщения в чат ---
    try:
        if admin:
            chat = db.query(AppChatModel).filter(
                ((AppChatModel.user1_id == current_user.id) & (AppChatModel.user2_id == admin.id)) |
                ((AppChatModel.user1_id == admin.id) & (AppChatModel.user2_id == current_user.id))
            ).first()
            if not chat:
                chat = AppChatModel(user1_id=current_user.id, user2_id=admin.id)
                db.add(chat)
                db.commit()
            chat_msg = AppChatMessageModel(
                chat_id=chat.id,
                sender_id=current_user.id,
                content=ticket.description,
                is_read=False
            )
            db.add(chat_msg)
            db.commit()
    except Exception as e:
        print(f"[ERROR] Не удалось создать чат или сообщение: {e}")
    
    print(f"DEBUG: Возвращаю тикет {ticket.id}")
    return ticket


@router.get("/tickets/{ticket_id}", response_model=schemas.Ticket)
def read_ticket(
    *,
    db: Session = Depends(deps.get_db),
    ticket_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    ticket = services.ticket.get(db=db, id=ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    
    if ticket.user_id != current_user.id and not services.user.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра этого тикета",
        )
    
    return ticket


@router.put("/tickets/{ticket_id}", response_model=schemas.Ticket)
def update_ticket(
    *,
    db: Session = Depends(deps.get_db),
    ticket_id: int,
    ticket_in: schemas.TicketUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    ticket = services.ticket.get(db=db, id=ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    
    if not services.user.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администраторы могут обновлять статус тикетов",
        )
    
    ticket = services.ticket.update(db=db, db_obj=ticket, obj_in=ticket_in)
    return ticket


@router.post("/tickets/{ticket_id}/responses", response_model=schemas.TicketResponse)
def create_ticket_response(
    *,
    db: Session = Depends(deps.get_db),
    ticket_id: int,
    response_in: schemas.TicketResponseCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    ticket = services.ticket.get(db=db, id=ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    
    is_from_admin = services.user.is_admin(current_user)
    
    if ticket.user_id != current_user.id and not is_from_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не можете отвечать на этот тикет",
        )
    
    response = services.ticket_response.create_response(
        db=db, obj_in=response_in, is_from_admin=is_from_admin
    )
    return response


@router.get("/tickets/{ticket_id}/responses", response_model=List[schemas.TicketResponse])
def read_ticket_responses(
    *,
    db: Session = Depends(deps.get_db),
    ticket_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    ticket = services.ticket.get(db=db, id=ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    
    if ticket.user_id != current_user.id and not services.user.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра ответов на этот тикет",
        )
    
    responses = services.ticket_response.get_ticket_responses(
        db=db, ticket_id=ticket_id, skip=skip, limit=limit
    )
    return responses 