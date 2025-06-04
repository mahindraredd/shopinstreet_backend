from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    password = Column(String)
    cart_items = relationship("CartItem", back_populates="user")


class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer)
    quantity = Column(Integer)
    status = Column(String, default="in_cart")
    
    user = relationship("User", back_populates="cart_items")


class ShippingDetails(Base):
    __tablename__ = "shipping_details"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    full_name = Column(String)        
    address = Column(String)
    city = Column(String)
    state = Column(String)
    country = Column(String)
    pincode = Column(String)
    phone = Column(String)
    email = Column(String)

