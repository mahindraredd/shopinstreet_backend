# app/schemas/vendor.py
# Updated schemas to match enterprise vendor model

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# Existing schemas (keep these)
class VendorRegister(BaseModel):
    business_name: str
    business_category: str
    address: str
    city: str
    state: str
    pincode: str
    country: str
    owner_name: str
    email: EmailStr
    phone: str
    password: str
    verification_type: str
    verification_number: str
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    business_logo: Optional[str] = None

class VendorLogin(BaseModel):
    email: EmailStr
    password: str

class VendorOut(BaseModel):
    """Enterprise vendor output schema with all fields"""
    id: int
    business_name: str
    business_category: str
    business_type: Optional[str] = None
    business_description: Optional[str] = None
    address: str
    city: str
    state: str
    pincode: str
    country: str
    owner_name: str
    email: str
    phone: str
    alternate_email: Optional[str] = None
    alternate_phone: Optional[str] = None
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    business_logo: Optional[str] = None
    business_hours: Optional[str] = None
    timezone: str = "America/Toronto"
    currency: str = "CAD"
    
    # Tax information
    gst_number: Optional[str] = None
    hst_pst_number: Optional[str] = None
    pan_card: Optional[str] = None
    business_registration_number: Optional[str] = None
    tax_exemption_status: bool = False
    
    # Banking (masked for security)
    bank_name: Optional[str] = None
    account_holder_name: Optional[str] = None
    # Note: account_number and routing_code are not included for security
    
    # Status and compliance
    is_verified: bool
    profile_completed: bool = False
    profile_completion_percentage: int = 0
    risk_score: int = 0
    compliance_status: str = "pending"
    
    # Timestamps
    created_at: datetime
    profile_updated_at: Optional[datetime] = None
    last_compliance_check: Optional[datetime] = None

    class Config:
        from_attributes = True

# 🆕 NEW SCHEMAS FOR UPDATES

class VendorProfileUpdate(BaseModel):
    """Schema for updating vendor profile information"""
    business_name: Optional[str] = None
    business_category: Optional[str] = None
    business_type: Optional[str] = None
    business_description: Optional[str] = None
    owner_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = None
    alternate_email: Optional[str] = None
    alternate_phone: Optional[str] = None
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    business_hours: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    
    # Tax information
    gst_number: Optional[str] = None
    hst_pst_number: Optional[str] = None
    pan_card: Optional[str] = None
    business_registration_number: Optional[str] = None
    tax_exemption_status: Optional[bool] = None

    class Config:
        from_attributes = True

class VendorBankingUpdate(BaseModel):
    """Schema for updating vendor banking information"""
    bank_name: Optional[str] = None
    account_number: Optional[str] = None  # Will be encrypted
    routing_code: Optional[str] = None    # Will be encrypted
    account_holder_name: Optional[str] = None

    class Config:
        from_attributes = True

class VendorNotificationSettings(BaseModel):
    """Schema for vendor notification preferences"""
    email_notifications: Optional[bool] = True
    order_updates: Optional[bool] = True
    low_stock_alerts: Optional[bool] = True
    marketing_emails: Optional[bool] = False
    weekly_reports: Optional[bool] = True

    class Config:
        from_attributes = True

# Enterprise analytics schemas
class VendorProfileCompletion(BaseModel):
    """Schema for profile completion response"""
    profile_completion_percentage: int
    profile_completed: bool
    missing_fields: list[str]
    suggestions: list[str]

class VendorRiskAssessment(BaseModel):
    """Schema for risk assessment response"""
    risk_score: int
    compliance_status: str
    risk_factors: list[str]
    recommendations: list[str]