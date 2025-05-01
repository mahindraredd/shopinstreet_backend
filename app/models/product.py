from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from sqlalchemy.dialects.postgresql import JSON

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    image_urls = Column(JSON, default=list)  # Store image URLs as JSON
    stock = Column(Integer, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendor.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    price = Column(Float, nullable=False, default=0.0)
    pricing_tiers = relationship("ProductPricingTier", back_populates="product", cascade="all, delete")


class ProductPricingTier(Base):
    __tablename__ = "product_pricing_tiers"

    id = Column(Integer, primary_key=True, index=True)
    moq = Column(Integer, nullable=False)  # Minimum Order Quantity
    price = Column(Float, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    product = relationship("Product", back_populates="pricing_tiers")

