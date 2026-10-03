from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Order
from ..schemas import OrderIn, OrderOut
from ..services import build_line

router = APIRouter(prefix="/api/orders", tags=["orders"])


def get_order_or_404(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    return order


@router.get("", response_model=list[OrderOut])
def list_orders(paid: bool | None = None, db: Session = Depends(get_db)):
    query = select(Order).options(selectinload(Order.lines)).order_by(Order.id.desc())
    if paid is not None:
        query = query.where(Order.paid == paid)
    return db.scalars(query).all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    return get_order_or_404(db, order_id)


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderIn, db: Session = Depends(get_db)):
    order = Order(paid=payload.paid, lines=[build_line(db, line) for line in payload.lines])
    db.add(order)
    db.commit()
    return order


@router.put("/{order_id}", response_model=OrderOut)
def replace_order(order_id: int, payload: OrderIn, db: Session = Depends(get_db)):
    order = get_order_or_404(db, order_id)
    order.paid = payload.paid
    order.lines = [build_line(db, line) for line in payload.lines]
    db.commit()
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = get_order_or_404(db, order_id)
    db.delete(order)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
