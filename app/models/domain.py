from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Enum, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
import enum
from datetime import datetime
from typing import Dict, Optional

class DomainStatus(str, enum.Enum):
    """Domain status enum for tracking domain lifecycle"""
    AVAILABLE = "available"
    PENDING_PURCHASE = "pending_purchase"
    PURCHASED = "purchased"
    DNS_CONFIGURING = "dns_configuring"
    HOSTING_SETUP = "hosting_setup"
    ACTIVE = "active"
    EXPIRED = "expired"
    FAILED = "failed"
    VERIFICATION_PENDING = "verification_pending"

class DomainType(str, enum.Enum):
    """Domain type enum"""
    CUSTOM = "custom"          # User's existing domain
    PURCHASED = "purchased"    # Domain bought through platform
    SUBDOMAIN = "subdomain"    # businessname.vision.com

class PaymentStatus(str, enum.Enum):
    """Payment status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class RegistrarType(str, enum.Enum):
    """Supported registrars"""
    GODADDY = "godaddy"
    NAMECHEAP = "namecheap"

class DomainOrder(Base):
    """
    Production-ready domain order model for Indian market
    Tracks complete domain purchase and setup lifecycle
    """
    __tablename__ = "domain_orders"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendor.id"), nullable=False, index=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Domain details
    domain_name = Column(String(255), nullable=False, index=True)
    domain_type = Column(Enum(DomainType), nullable=False)
    template_id = Column(Integer, nullable=False)
    
    # Pricing in INR (Indian Rupees)
    domain_price_inr = Column(Float, nullable=False)
    hosting_price_inr = Column(Float, default=0.0)
    ssl_price_inr = Column(Float, default=0.0)
    total_amount_inr = Column(Float, nullable=False)
    
    # Payment details
    payment_method = Column(String(50), nullable=True)  # razorpay, payu, etc.
    payment_id = Column(String(100), nullable=True, index=True)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, index=True)
    razorpay_order_id = Column(String(100), nullable=True)
    razorpay_payment_id = Column(String(100), nullable=True)
    
    # Order status tracking
    order_status = Column(Enum(DomainStatus), default=DomainStatus.PENDING_PURCHASE, index=True)
    completion_percentage = Column(Integer, default=0)
    current_step = Column(String(100), default="payment_pending")
    
    # Registrar details (GoDaddy or Namecheap)
    selected_registrar = Column(Enum(RegistrarType), nullable=True)
    domain_registration_id = Column(String(100), nullable=True)
    registrar_order_id = Column(String(100), nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    
    # Technical setup status
    dns_configured = Column(Boolean, default=False)
    ssl_enabled = Column(Boolean, default=False)
    hosting_active = Column(Boolean, default=False)
    nameservers_updated = Column(Boolean, default=False)
    
    # Error handling and retries
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Contact information for domain registration
    contact_info = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)
    payment_confirmed_at = Column(DateTime, nullable=True)
    
    # Relationships
    vendor = relationship("Vendor", back_populates="domain_orders")
    
    def __repr__(self):
        return f"<DomainOrder {self.order_number}: {self.domain_name} - {self.order_status}>"

class VendorDomain(Base):
    """
    Production domain model for active vendor domains
    Created after successful domain order completion
    """
    __tablename__ = "vendor_domains"
    
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendor.id"), nullable=False, index=True)
    domain_name = Column(String(255), nullable=False, unique=True, index=True)
    domain_type = Column(Enum(DomainType), nullable=False)
    status = Column(Enum(DomainStatus), default=DomainStatus.ACTIVE, index=True)
    
    # Indian market pricing
    purchase_price_inr = Column(Float, nullable=True)
    renewal_price_inr = Column(Float, nullable=True)
    
    # Registrar information
    registrar = Column(Enum(RegistrarType), nullable=True)
    registration_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True, index=True)  # For renewal tracking
    
    # Technical configuration
    ssl_enabled = Column(Boolean, default=False)
    dns_configured = Column(Boolean, default=False)
    hosting_active = Column(Boolean, default=False)
    
    # Template and hosting details
    template_id = Column(Integer, nullable=True)
    hosting_server = Column(String(100), nullable=True)
    
    # Reference to original order
    domain_order_id = Column(Integer, ForeignKey("domain_orders.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    vendor = relationship("Vendor", back_populates="domains")
    domain_order = relationship("DomainOrder")
    
    def __repr__(self):
        return f"<VendorDomain {self.domain_name}: {self.status}>"

class DomainSuggestion(Base):
    """
    Enhanced domain suggestion model with Indian TLD support
    Caches domain suggestions for performance
    """
    __tablename__ = "domain_suggestions"
    
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendor.id"), nullable=False, index=True)
    business_name = Column(String(255), nullable=False, index=True)
    suggested_domain = Column(String(255), nullable=False, index=True)
    tld = Column(String(10), nullable=False, index=True)  # .com, .in, .co.in, etc.
    
    # Indian market pricing in INR
    registration_price_inr = Column(Float, nullable=False)
    renewal_price_inr = Column(Float, nullable=False)
    
    # Availability and scoring
    is_available = Column(Boolean, default=True, index=True)
    is_premium = Column(Boolean, default=False)
    recommendation_score = Column(Float, default=0.0)  # 0-1 score
    is_popular_tld = Column(Boolean, default=False)
    
    # Registrar pricing comparison
    godaddy_price_inr = Column(Float, nullable=True)
    namecheap_price_inr = Column(Float, nullable=True)
    best_registrar = Column(Enum(RegistrarType), nullable=True)
    
    # Cache management
    availability_checked_at = Column(DateTime, default=func.now())
    cache_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<DomainSuggestion {self.suggested_domain}: ₹{self.registration_price_inr}>"
