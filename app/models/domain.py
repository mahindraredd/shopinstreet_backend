# app/models/domain.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
import enum

class DomainStatus(str, enum.Enum):
    AVAILABLE = "available"
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    FAILED = "failed"

class DomainType(str, enum.Enum):
    CUSTOM = "custom"          # User's existing domain
    PURCHASED = "purchased"    # Domain bought through platform
    SUBDOMAIN = "subdomain"    # businessname.vision.com

class VendorDomain(Base):
    __tablename__ = "vendor_domains"
    
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendor.id"), nullable=False, index=True)
    domain_name = Column(String(255), nullable=False, unique=True, index=True)
    domain_type = Column(Enum(DomainType), nullable=False)
    status = Column(Enum(DomainStatus), default=DomainStatus.PENDING)
    
    # Domain purchase info
    purchase_price = Column(Float, nullable=True)
    renewal_price = Column(Float, nullable=True)
    registration_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    
    # Technical details
    ssl_enabled = Column(Boolean, default=False)
    dns_configured = Column(Boolean, default=False)
    hosting_active = Column(Boolean, default=False)
    
    # Template configuration
    template_id = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    vendor = relationship("Vendor", back_populates="domains")

class DomainSuggestion(Base):
    __tablename__ = "domain_suggestions"
    
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendor.id"), nullable=False)
    business_name = Column(String(255), nullable=False)
    suggested_domain = Column(String(255), nullable=False, index=True)
    tld = Column(String(10), nullable=False)  # .com, .net, .shop, etc.
    
    # Pricing
    registration_price = Column(Float, nullable=False)
    renewal_price = Column(Float, nullable=False)
    
    # Availability
    is_available = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    recommendation_score = Column(Float, default=0.0)  # 0-1 score
    is_popular_tld = Column(Boolean, default=False)
    
    # Cache info
    availability_checked_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())