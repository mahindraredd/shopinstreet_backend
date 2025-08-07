# app/schemas/domain.py - INDIAN MARKET VERSION
from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

# ========================================
# DOMAIN SUGGESTION SCHEMAS
# ========================================

class DomainSuggestionOut(BaseModel):
    """Domain suggestion for Indian market with INR pricing"""
    suggested_domain: str
    tld: str
    
    # Indian market pricing in INR
    registration_price_inr: float
    renewal_price_inr: float
    registration_price_display: str = Field(default="")  # ₹999
    renewal_price_display: str = Field(default="")      # ₹1,199
    
    # Availability and features
    is_available: bool = True
    is_premium: bool = False
    is_popular_tld: bool
    recommendation_score: float = Field(ge=0.0, le=1.0)
    
    # Indian market features
    hosting_included: bool = True
    ssl_included: bool = True
    setup_time: str = "24-48 hours"
    registrar: str = "godaddy"
    
    # Format price displays automatically
    def __init__(self, **data):
        super().__init__(**data)
        if not self.registration_price_display:
            self.registration_price_display = f"₹{self.registration_price_inr:,.0f}"
        if not self.renewal_price_display:
            self.renewal_price_display = f"₹{self.renewal_price_inr:,.0f}"
    
    class Config:
        from_attributes = True

class DomainSuggestionResponse(BaseModel):
    """Indian market domain suggestions response"""
    success: bool = True
    suggestions: List[DomainSuggestionOut]
    business_name: str
    total_suggestions: int
    
    # Indian market specifics
    currency: str = "INR"
    market: str = "India"
    cheapest_price_inr: Optional[float] = None
    
    # Set cheapest price automatically
    def __init__(self, **data):
        super().__init__(**data)
        if self.suggestions and not self.cheapest_price_inr:
            self.cheapest_price_inr = min(s.registration_price_inr for s in self.suggestions)

# ========================================
# CONTACT & PURCHASE SCHEMAS
# ========================================

class ContactInfoSchema(BaseModel):
    """Contact information for Indian domain registration"""
    name: str = Field(..., min_length=2, max_length=100, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    phone: str = Field(..., min_length=10, max_length=15, description="Phone number with country code")
    organization: Optional[str] = Field(None, max_length=100, description="Company/Organization name")
    
    # Indian address format
    address: str = Field(..., min_length=10, max_length=200, description="Street address")
    city: str = Field(..., min_length=2, max_length=50, description="City")
    state: str = Field(default="Karnataka", max_length=50, description="Indian state")
    postal_code: str = Field(..., min_length=6, max_length=6, description="6-digit PIN code")
    country: str = Field(default="India", description="Country")
    
    @validator('phone')
    def validate_indian_phone(cls, v):
        """Validate Indian phone number"""
        # Remove all non-digit characters
        clean_phone = ''.join(filter(str.isdigit, v))
        
        # Indian mobile numbers are 10 digits, landline can be 10-11
        if len(clean_phone) < 10 or len(clean_phone) > 11:
            raise ValueError('Indian phone number must be 10-11 digits')
        
        # Indian mobile numbers start with 6, 7, 8, or 9
        if len(clean_phone) == 10 and clean_phone[0] not in '6789':
            raise ValueError('Invalid Indian mobile number format')
        
        return clean_phone
    
    @validator('postal_code')
    def validate_indian_pincode(cls, v):
        """Validate Indian PIN code"""
        clean_pin = ''.join(filter(str.isdigit, v))
        if len(clean_pin) != 6:
            raise ValueError('Indian PIN code must be exactly 6 digits')
        return clean_pin
    
    @validator('state')
    def validate_indian_state(cls, v):
        """Validate Indian state"""
        indian_states = [
            'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
            'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
            'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
            'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
            'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
            'Delhi', 'Puducherry', 'Chandigarh', 'Jammu and Kashmir', 'Ladakh'
        ]
        if v not in indian_states:
            # Allow the value but could warn
            pass
        return v

class DomainPurchaseRequest(BaseModel):
    """Domain purchase request for Indian market"""
    domain_name: str = Field(..., min_length=4, max_length=253, description="Domain name to purchase")
    template_id: int = Field(..., ge=1, le=10, description="Website template ID")
    contact_info: ContactInfoSchema
    payment_method: str = Field(default="razorpay", description="Payment gateway: razorpay, payu")
    registration_years: int = Field(default=1, ge=1, le=5, description="Registration years")
    
    @validator('domain_name')
    def validate_domain(cls, v):
        """Validate domain name format"""
        if not v or '.' not in v:
            raise ValueError('Please enter a valid domain name')
        
        # Basic domain format validation
        import re
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid domain format')
        return v.lower()
    
    @validator('payment_method')
    def validate_payment_method(cls, v):
        """Validate Indian payment methods"""
        allowed_methods = ['razorpay', 'payu', 'test']  # Added 'test' for development
        if v.lower() not in allowed_methods:
            raise ValueError(f'Payment method must be one of: {", ".join(allowed_methods)}')
        return v.lower()

class DomainPurchaseResponse(BaseModel):
    """Domain purchase response"""
    success: bool
    order_id: Optional[int] = None
    order_number: Optional[str] = None
    domain_name: Optional[str] = None
    total_amount_inr: Optional[float] = None
    registrar: Optional[str] = "godaddy"
    message: str
    error: Optional[str] = None
    
    # Indian payment specifics
    payment_gateway: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    estimated_completion: str = "24-48 hours"

# ========================================
# ORDER STATUS SCHEMAS  
# ========================================

class OrderStep(BaseModel):
    """Order processing step"""
    step_name: str
    status: str  # pending, in_progress, completed, failed
    description: str
    completion_percentage: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class OrderStatusResponse(BaseModel):
    """Detailed order status for Indian market"""
    order_id: int
    order_number: Optional[str] = None
    domain_name: str
    status: str  # pending_purchase, purchased, dns_configuring, hosting_setup, active, failed
    completion_percentage: int = Field(ge=0, le=100)
    current_step: str
    
    # Payment information
    payment_status: str = "pending"
    total_amount_inr: Optional[float] = None
    
    # Technical details
    registrar: str = "godaddy"
    template_id: Optional[int] = None
    ssl_enabled: bool = False
    hosting_active: bool = False
    
    # Timestamps
    created_at: Optional[str] = None
    payment_confirmed_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Results
    website_url: Optional[str] = None
    error_message: Optional[str] = None
    
    # Processing info
    is_processing: bool = False
    using_mock: bool = False
    estimated_completion: str = "24-48 hours"

# ========================================
# EXISTING DOMAIN CONNECTION
# ========================================

class ExistingDomainRequest(BaseModel):
    """Connect existing domain request"""
    domain_name: str = Field(..., min_length=4, max_length=253)
    registrar: str = Field(..., min_length=2, max_length=50, description="Current registrar")
    template_id: int = Field(..., ge=1, le=10)
    
    @validator('domain_name')
    def validate_domain(cls, v):
        """Validate domain format"""
        if not v or '.' not in v:
            raise ValueError('Please enter a valid domain name')
        import re
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid domain format')
        return v.lower()

# ========================================
# VENDOR DOMAIN SCHEMAS
# ========================================


class VendorDomainOut(BaseModel):
    """Vendor domain output for Indian market"""
    id: int
    domain_name: str
    type: str  # purchased, custom, subdomain
    status: str  # active, pending, expired, failed
    
    # Template and hosting
    template_id: Optional[int] = None
    ssl_enabled: bool = False
    dns_configured: bool = False
    hosting_active: bool = False
    
    # Indian market pricing
    purchase_price_inr: Optional[float] = None
    renewal_price_inr: Optional[float] = None
    purchase_price_display: Optional[str] = None
    renewal_price_display: Optional[str] = None
    
    # Technical details
    registrar: Optional[str] = None
    expiry_date: Optional[str] = None
    created_at: str
    
    # Access URL
    website_url: str
    
    # Format prices automatically
    def __init__(self, **data):
        super().__init__(**data)
        if self.purchase_price_inr and not self.purchase_price_display:
            self.purchase_price_display = f"₹{self.purchase_price_inr:,.0f}"
        if self.renewal_price_inr and not self.renewal_price_display:
            self.renewal_price_display = f"₹{self.renewal_price_inr:,.0f}"
    
    class Config:
        from_attributes = True

# ========================================
# TEMPLATE SCHEMAS
# ========================================


class TemplateInfo(BaseModel):
    """Website template information"""
    id: int
    name: str
    description: str
    category: str
    preview_url: str
    features: List[str]
    suitable_for: List[str]
    
    # Indian market specifics
    setup_time: str = "24-48 hours"
    includes_hosting: bool = True
    includes_ssl: bool = True
    mobile_optimized: bool = True

# ========================================
# VALIDATION SCHEMAS
# ========================================

class DomainValidationResponse(BaseModel):
    """Domain validation response"""
    domain: str
    valid: bool
    available: Optional[bool] = None
    errors: List[str] = []
    suggestions: List[str] = []
    
    # Indian market checks
    supports_indian_tld: bool = True
    estimated_price_inr: Optional[float] = None

# ========================================
# SERVICE HEALTH SCHEMAS
# ========================================

class DomainServiceHealth(BaseModel):
    """Domain service health status"""
    service: str = "Indian Domain Service"
    status: str = "operational"
    version: str = "1.0.0"
    
    # Market specifics
    market: str = "India"
    currency: str = "INR"
    supported_tlds: List[str]
    registrar: str = "godaddy"
    
    # Service status
    using_mock: bool = False
    godaddy_status: str = "online"
    features: List[str]

# ========================================
# BULK AVAILABILITY SCHEMAS
# ========================================

class BulkAvailabilityRequest(BaseModel):
    """Check multiple domains availability"""
    domains: List[str] = Field(..., max_items=20, description="List of domains to check")
    
    @validator('domains')
    def validate_domains(cls, v):
        """Validate all domains in the list"""
        if len(v) == 0:
            raise ValueError('At least one domain is required')
        
        import re
        for domain in v:
            if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}$', domain):
                raise ValueError(f'Invalid domain format: {domain}')
        
        return [domain.lower() for domain in v]

class DomainAvailabilityResult(BaseModel):
    """Single domain availability result"""
    domain: str
    available: bool
    price_inr: Optional[float] = None
    registrar: str = "godaddy"
    checked_at: str
    response_time_ms: Optional[int] = None
    error: Optional[str] = None

class BulkAvailabilityResponse(BaseModel):
    """Bulk domain availability response"""
    success: bool = True
    results: Dict[str, DomainAvailabilityResult]
    total_checked: int
    available_count: int
    check_time_ms: int
    currency: str = "INR"