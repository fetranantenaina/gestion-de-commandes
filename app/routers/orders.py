from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OrderStatus
from app.schemas import OrderCreate, OrderOut
from app.services import orders as service

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    return service.create_order(db, payload.items)


@router.get("", response_model=list[OrderOut])
def list_orders(status: OrderStatus | None = None, db: Session = Depends(get_db)):
    return service.list_orders(db, status)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    return service.get_order(db, order_id)


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    return service.cancel_order(db, order_id)


@router.post("/{order_id}/validate", response_model=OrderOut)
def validate_order(order_id: int, db: Session = Depends(get_db)):
    return service.validate_order(db, order_id)
