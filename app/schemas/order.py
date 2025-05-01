from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.order import OrderStatus

class OrderItemCreate(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    price: float

class OrderCreate(BaseModel):
    customer_name: str
    customer_email: str
    customer_phone: int
    shipping_address: str
    total_amount: float
    order_items: List[OrderItemCreate]

class OrderItemOut(OrderItemCreate):
    id: int

class OrderOut(BaseModel):
    id: int
    customer_name: str
    customer_email: str
    shipping_address: str
    total_amount: float
    status: OrderStatus
    created_at: datetime
    order_items: List[OrderItemOut]

class OrderStatusUpdate(BaseModel):
    status: str  # e.g., "pending", "processing", "shipped", "delivered"

    class Config:
        orm_mode = True
