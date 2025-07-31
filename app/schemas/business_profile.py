# app/schemas/business_profile.py - Simplified Pydantic v2 Compatible

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Simple Enums
class BusinessType(str, Enum):
    SOLE_PROPRIETORSHIP = "sole_proprietorship"
    PARTNERSHIP = "partnership"
    PRIVATE_LIMITED = "private_limited"
    CORPORATION = "corporation"
    LLP = "llp"

class Currency(str, Enum):
    USD = "USD"
    CAD = "CAD"
    INR = "INR"

# Simple Request Schema
class BusinessProfileUpdateRequest(BaseModel):
    """Simplified schema for updating business profile"""
    
    # Basic Business Information
    business_name: Optional[str] = Field(None, min_length=2, max_length=100)
    business_type: Optional[str] = None
    business_category: Optional[str] = Field(None, min_length=2, max_length=50)
    business_description: Optional[str] = Field(None, max_length=1000)
    
    # Contact Information
    owner_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    alternate_email: Optional[EmailStr] = None
    alternate_phone: Optional[str] = Field(None, min_length=10, max_length=15)
    
    # Address Information
    address: Optional[str] = Field(None, min_length=5, max_length=200)
    city: Optional[str] = Field(None, min_length=2, max_length=50)
    state: Optional[str] = Field(None, min_length=2, max_length=50)
    pincode: Optional[str] = Field(None, min_length=3, max_length=10)
    country: Optional[str] = Field(None, min_length=2, max_length=50)
    
    # Tax & Legal Information
    gst_number: Optional[str] = Field(None, max_length=15)
    hst_pst_number: Optional[str] = Field(None, max_length=20)
    pan_card: Optional[str] = Field(None, max_length=10)
    business_registration_number: Optional[str] = Field(None, max_length=50)
    tax_exemption_status: Optional[bool] = None
    
    # Banking Information
    bank_name: Optional[str] = Field(None, max_length=100)
    account_number: Optional[str] = Field(None, min_length=4, max_length=20)
    routing_code: Optional[str] = Field(None, min_length=4, max_length=15)
    account_holder_name: Optional[str] = Field(None, max_length=100)
    
    # Optional Information
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    
    # Business Operations
    timezone: Optional[str] = Field(None, max_length=50)
    currency: Optional[str] = None

class BankingInfoUpdateRequest(BaseModel):
    """Schema for banking information updates"""
    
    bank_name: Optional[str] = Field(None, max_length=100)
    account_number: Optional[str] = Field(None, min_length=4, max_length=20)
    routing_code: Optional[str] = Field(None, min_length=4, max_length=15)
    account_holder_name: Optional[str] = Field(None, max_length=100)

# Simple Response Schema
class BusinessProfileResponse(BaseModel):
    """Simple business profile response"""
    
    # Basic Information
    id: int
    business_name: str
    business_type: Optional[str] = None
    business_category: str
    business_description: Optional[str] = None
    
    # Contact Information
    owner_name: str
    email: EmailStr
    phone: str
    alternate_email: Optional[str] = None
    alternate_phone: Optional[str] = None
    
    # Address Information
    address: str
    city: str
    state: str
    pincode: str
    country: str
    
    # Tax & Legal Information
    gst_number: Optional[str] = None
    hst_pst_number: Optional[str] = None
    pan_card_masked: Optional[str] = None
    business_registration_number: Optional[str] = None
    tax_exemption_status: bool = False
    
    # Banking Information (masked)
    bank_name: Optional[str] = None
    account_number_masked: Optional[str] = None
    routing_code: Optional[str] = None
    account_holder_name: Optional[str] = None
    
    # Optional Information
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    business_logo: Optional[str] = None
    
    # Business Operations
    timezone: str = "UTC"
    currency: str = "USD"
    
    # Status Information
    is_verified: bool = False
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

# Simple Status Responses
class ProfileCompletionResponse(BaseModel):
    """Profile completion status"""
    
    completion_percentage: int = Field(..., ge=0, le=100)
    is_profile_complete: bool
    completed_sections: List[str]
    missing_sections: List[str]
    next_recommended_action: str
    priority_missing_fields: List[str]

class ComplianceStatusResponse(BaseModel):
    """Compliance status information"""
    
    risk_score: int = Field(..., ge=0, le=100)
    compliance_status: str
    last_check: Optional[datetime] = None
    compliance_issues: List[str] = []
    recommendations: List[str] = []

class CountryRequirementsResponse(BaseModel):
    """Country-specific requirements"""
    
    country: str
    required_tax_fields: List[str]
    optional_tax_fields: List[str]
    banking_requirements: Dict[str, str]
    sample_formats: Dict[str, str]
    supported_currencies: List[str]

class FieldValidationResponse(BaseModel):
    """Field validation response"""
    
    field_name: str
    is_valid: bool
    error_message: Optional[str] = None
    suggestions: List[str] = []

# Standard Response Schemas
class SuccessResponse(BaseModel):
    """Standard success response"""
    
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    """Standard error response"""
    
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

# Bulk Operations
class BulkProfileUpdateRequest(BaseModel):
    """Bulk profile update request"""
    
    vendor_ids: List[int] = Field(..., min_length=1, max_length=100)
    updates: BusinessProfileUpdateRequest

class BulkOperationResponse(BaseModel):
    """Bulk operation response"""
    
    total_requested: int
    successful_updates: int
    failed_updates: int
    success_ids: List[int]
    failed_ids: List[Dict[str, Any]]