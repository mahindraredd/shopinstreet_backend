from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.session import Base  # Shared declarative base
from sqlalchemy.orm import relationship
class Vendor(Base):
    __tablename__ = "vendor"  # This will be the actual table name in PostgreSQL

    id = Column(Integer, primary_key=True, index=True)

    # Business Info
    business_name = Column(String, nullable=False)
    business_category = Column(String, nullable=False)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    pincode = Column(String, nullable=False)
    country = Column(String, nullable=False)

    # Contact Info
    owner_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, unique=True, nullable=False)

    # Auth
    password_hash = Column(String, nullable=False)

    # Verification
    verification_type = Column(String, nullable=False)
    verification_number = Column(String, nullable=False)

    # Optional
    website_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    business_logo = Column(String, nullable=True)

    # Status
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    orders = relationship("Order", back_populates="vendor", cascade="all, delete-orphan")

    # Store Template Selection
    template_id = Column(Integer, default=1, nullable=True)
