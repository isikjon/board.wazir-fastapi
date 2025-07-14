from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.request import Request, RequestStatus
from app.schemas.request import RequestCreate, RequestUpdate


class CRUDRequest:
    def create(self, db: Session, *, obj_in: RequestCreate, user_id: int) -> Request:
        """Создание новой заявки"""
        db_obj = Request(
            **obj_in.dict(),
            user_id=user_id,
            status=RequestStatus.NEW
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get(self, db: Session, id: int) -> Optional[Request]:
        """Получение заявки по ID"""
        return db.query(Request).filter(Request.id == id).first()
    
    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, user_id: Optional[int] = None
    ) -> List[Request]:
        """Получение списка заявок с возможной фильтрацией по пользователю"""
        query = db.query(Request)
        if user_id is not None:
            query = query.filter(Request.user_id == user_id)
        return query.order_by(desc(Request.created_at)).offset(skip).limit(limit).all()
    
    def get_by_status(
        self, db: Session, *, status: RequestStatus, skip: int = 0, limit: int = 100
    ) -> List[Request]:
        """Получение списка заявок по статусу"""
        return (
            db.query(Request)
            .filter(Request.status == status)
            .order_by(desc(Request.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def update(
        self, db: Session, *, db_obj: Request, obj_in: RequestUpdate
    ) -> Request:
        """Обновление заявки"""
        update_data = obj_in.dict(exclude_unset=True)
        
        for field in update_data:
            setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update_status(self, db: Session, *, db_obj: Request, status: RequestStatus) -> Request:
        """Обновление статуса заявки"""
        db_obj.status = status
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, *, id: int) -> None:
        """Удаление заявки"""
        obj = db.query(Request).get(id)
        db.delete(obj)
        db.commit()


request = CRUDRequest() 