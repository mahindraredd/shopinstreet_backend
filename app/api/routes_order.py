from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.deps import get_db, get_current_vendor
from app.schemas.order import OrderCreate, OrderOut, OrderStatusUpdate
from app.crud import order as crud_order
from app.models.order import Order
from app.models.vendor import Vendor
from typing import List

router = APIRouter()

@router.post("/", response_model=OrderOut)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    return crud_order.create_order(db, order_data, vendor.id)

@router.get("/mine", response_model=List[OrderOut])
def list_my_orders(
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    return crud_order.get_orders_by_vendor(db, vendor.id)

@router.put("/{order_id}", response_model=OrderOut)
def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    vendor = Depends(get_current_vendor)
):
    order = crud_order.update_order_status(db, order_id, status_data.status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
