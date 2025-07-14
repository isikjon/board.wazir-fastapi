from typing import Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from app import models, schemas, services
from app.api import deps
from app.models.request import RequestStatus

router = APIRouter()


@router.get("/", response_model=List[schemas.Request])
def read_requests(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Получение списка заявок.
    Для обычных пользователей - только свои заявки.
    Для админов - все заявки.
    """
    if services.user.is_admin(current_user):
        return services.request.get_multi(db=db, skip=skip, limit=limit)
    return services.request.get_multi(
        db=db, skip=skip, limit=limit, user_id=current_user.id
    )


@router.post("/", response_model=schemas.Request)
def create_request(
    *,
    db: Session = Depends(deps.get_db),
    request_in: schemas.RequestCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Создание новой заявки.
    """
    request = services.request.create(db=db, obj_in=request_in, user_id=current_user.id)
    return request


@router.get("/{id}", response_model=schemas.Request)
def read_request(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Получение заявки по ID.
    """
    request = services.request.get(db=db, id=id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if not services.user.is_admin(current_user) and request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return request


@router.put("/{id}", response_model=schemas.Request)
def update_request(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    request_in: schemas.RequestUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Обновление заявки.
    """
    request = services.request.get(db=db, id=id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if not services.user.is_admin(current_user) and request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    request = services.request.update(db=db, db_obj=request, obj_in=request_in)
    return request


@router.put("/{id}/status", response_model=schemas.Request)
def update_request_status(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    status: RequestStatus,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Обновление статуса заявки.
    Только для админов.
    """
    if not services.user.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    request = services.request.get(db=db, id=id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request = services.request.update_status(db=db, db_obj=request, status=status)
    return request


@router.put("/{id}/appointment", response_model=schemas.Request)
def set_appointment_date(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    appointment_date: datetime = Body(..., embed=True),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Назначение даты встречи для заявки.
    Только для админов.
    """
    if not services.user.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    request = services.request.get(db=db, id=id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Обновляем только дату встречи
    update_data = {"appointment_date": appointment_date}
    if request.status == RequestStatus.NEW:
        update_data["status"] = RequestStatus.PROCESSING
    
    request = services.request.update(db=db, db_obj=request, obj_in=schemas.RequestUpdate(**update_data))
    return request


@router.put("/{id}/archive", response_model=schemas.Request)
def archive_request(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Архивирование заявки (переведение в статус 'completed').
    Только для админов.
    """
    if not services.user.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    request = services.request.get(db=db, id=id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request = services.request.update_status(db=db, db_obj=request, status=RequestStatus.COMPLETED)
    return request


@router.put("/{id}/approve", response_model=schemas.Request)
def approve_request(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Принятие заявки (переведение в статус 'processing').
    Только для админов.
    """
    if not services.user.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    request = services.request.get(db=db, id=id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request = services.request.update_status(db=db, db_obj=request, status=RequestStatus.PROCESSING)
    return request


@router.put("/{id}/reject", response_model=schemas.Request)
def reject_request(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Отклонение заявки (переведение в статус 'rejected').
    Только для админов.
    """
    if not services.user.is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    request = services.request.get(db=db, id=id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request = services.request.update_status(db=db, db_obj=request, status=RequestStatus.REJECTED)
    return request


@router.delete("/{id}", response_model=schemas.Msg)
def delete_request(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Удаление заявки.
    Админы могут удалять любые заявки.
    Пользователи могут удалять только свои заявки.
    """
    request = services.request.get(db=db, id=id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if not services.user.is_admin(current_user) and request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    services.request.delete(db=db, id=id)
    return {"msg": "Request deleted successfully"} 