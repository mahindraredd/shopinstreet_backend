from sqlalchemy import Column, Integer, String, ForeignKey, Float, Enum, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base
import enum

class OrderStatus(str, enum.Enum):
    pending = "Pending"
    processing = "Processing"
    shipped = "Shipped"
    delivered = "Delivered"

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=False)
    customer_phone = Column(String, nullable=True)
    shipping_address = Column(String, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)

    vendor_id = Column(Integer, ForeignKey("vendor.id"))
    vendor = relationship("Vendor", back_populates="orders")

    order_items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer)
    product_name = Column(String)
    quantity = Column(Integer)
    price = Column(Float)

    order_id = Column(Integer, ForeignKey("orders.id"))
    order = relationship("Order", back_populates="order_items")


