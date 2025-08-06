# app/schemas/domain.py - CLEAN FIXED VERSION
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class DomainSuggestionOut(BaseModel):
    """Enhanced domain suggestion with multi-registrar pricing"""
    suggested_domain: str
    tld: str
    
    # Customer pricing (what they see and pay)
    registration_price: float
    registration_price_display: Optional[str] = None  # Formatted with currency symbol
    renewal_price: float
    renewal_price_display: Optional[str] = None
    currency: Optional[str] = "USD"  # USD, INR, EUR, etc.
    currency_symbol: Optional[str] = "$"  # $, ₹, €, etc.
    
    # Availability and features
    is_available: bool
    is_premium: bool
    is_popular_tld: bool
    recommendation_score: float = Field(ge=0.0, le=1.0)
    
    # Business intelligence (internal data)
    wholesale_price: Optional[float] = None  # What we pay the registrar
    wholesale_registrar: Optional[str] = None  # Which registrar we'll use
    margin_amount: Optional[float] = None  # Our profit in USD
    margin_percent: Optional[float] = None  # Profit margin percentage
    response_time_ms: Optional[int] = None  # How fast the check was
    
    class Config:
        from_attributes = True

class DomainSuggestionResponse(BaseModel):
    """Enhanced response with market intelligence"""
    suggestions: List[DomainSuggestionOut]
    business_name: str
    total_suggestions: int
    search_time_ms: int
    
    # Geographic and market data
    customer_location: Optional[str] = "US"  # US, India, UK, etc.
    currency: Optional[str] = "USD"  # Primary currency for this customer
    currency_symbol: Optional[str] = "$"  # Symbol to display
    
    # Service performance metrics
    registrars_checked: Optional[int] = 0  # How many registrars we queried
    available_count: Optional[int] = 0  # How many domains are available
    cheapest_price: Optional[float] = 0  # Lowest price found
    
    # Value proposition
    average_savings: Optional[float] = None  # vs major competitors
    fastest_response_ms: Optional[int] = None  # Fastest registrar response

class DomainAvailabilityCheck(BaseModel):
    """Single domain availability with detailed registrar breakdown"""
    domain: str
    available: bool
    premium: bool = False
    
    # Customer pricing
    customer_price: float
    customer_currency: str
    customer_symbol: str
    price_display: str
    
    # Business data
    wholesale_price: float
    wholesale_registrar: str
    margin_amount: float
    margin_percent: float
    
    # Performance metrics
    checked_at: datetime
    response_time_ms: int
    registrars_checked: int
    fastest_registrar: Optional[str] = None
    
    # Detailed registrar responses
    registrar_details: List[Dict[str, Any]] = []

class RegistrarStatus(BaseModel):
    """Individual registrar status for monitoring"""
    registrar: str
    status: str  # online, offline, degraded
    response_time_ms: int
    reliability: float  # Historical uptime percentage
    avg_price: float  # Average pricing for this registrar
    last_checked: datetime

class RegistrarStatusResponse(BaseModel):
    """Overall registrar health status"""
    registrars: Dict[str, RegistrarStatus]
    summary: Dict[str, Any]

class DomainValidation(BaseModel):
    """Domain name validation result"""
    domain: str
    valid: bool
    errors: List[str] = []
    suggestions: List[str] = []  # Valid alternatives if invalid
    
    @validator('domain')
    def validate_domain_format(cls, v):
        """Validate domain name format"""
        if not v or len(v) < 4:
            raise ValueError('Domain must be at least 4 characters long')
        
        if not '.' in v:
            raise ValueError('Domain must include a TLD (e.g., .com)')
        
        # Basic domain format validation
        import re
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid domain format')
        
        return v.lower()

# Step 2: Purchase and Payment Schemas

class ContactInfoSchema(BaseModel):
    """Contact information for domain registration"""
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')  # FIXED: pattern instead of regex
    phone: str = Field(..., min_length=10, max_length=20)
    company: Optional[str] = Field(None, max_length=100)
    address_line1: str = Field(..., min_length=5, max_length=100)
    address_line2: Optional[str] = Field(None, max_length=100)
    city: str = Field(..., min_length=2, max_length=50)
    state: str = Field(..., min_length=2, max_length=50)
    postal_code: str = Field(..., min_length=3, max_length=20)
    country: str = Field(default="US", min_length=2, max_length=3)
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v or '.' not in v.split('@')[-1]:
            raise ValueError('Please enter a valid email address')
        return v.lower()
    
    @validator('phone')
    def validate_phone(cls, v):
        # Remove all non-digit characters
        clean_phone = ''.join(filter(str.isdigit, v))
        if len(clean_phone) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return clean_phone

class DomainPurchaseRequest(BaseModel):
    """Request to purchase a domain"""
    domain: str = Field(..., min_length=4, max_length=253)
    contact_info: ContactInfoSchema
    payment_method: str = Field(..., description="Payment method: credit_card, paypal, stripe")
    template_id: int = Field(..., ge=1, le=10, description="Website template ID")
    registration_years: int = Field(1, ge=1, le=10, description="Registration period in years")
    
    @validator('domain')
    def validate_domain(cls, v):
        if not v or '.' not in v:
            raise ValueError('Please enter a valid domain name')
        # Basic domain format validation
        import re
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid domain format')
        return v.lower()
    
    @validator('payment_method')
    def validate_payment_method(cls, v):
        allowed_methods = ['credit_card', 'paypal', 'stripe', 'bank_transfer']
        if v.lower() not in allowed_methods:
            raise ValueError(f'Payment method must be one of: {", ".join(allowed_methods)}')
        return v.lower()

class DomainPurchaseResponse(BaseModel):
    """Response from domain purchase request"""
    success: bool
    order_id: str
    domain: str
    amount: float
    currency: str
    status: str
    payment_methods: List[Dict[str, Any]]
    next_step: str
    message: str
    estimated_completion: Optional[str] = None

class PaymentDetailsSchema(BaseModel):
    """Payment details for different payment methods"""
    # Credit card details
    card_number: Optional[str] = Field(None, min_length=13, max_length=19)
    card_expiry: Optional[str] = Field(None, pattern=r'^\d{2}/\d{2}$')  # FIXED: pattern instead of regex
    card_cvv: Optional[str] = Field(None, min_length=3, max_length=4)
    cardholder_name: Optional[str] = Field(None, min_length=2, max_length=100)
    
    # PayPal details
    paypal_email: Optional[str] = None
    paypal_token: Optional[str] = None
    
    # Stripe details
    stripe_token: Optional[str] = None
    stripe_payment_method_id: Optional[str] = None
    
    # Bank transfer details
    bank_account: Optional[str] = None
    bank_routing: Optional[str] = None
    
    @validator('card_number')
    def validate_card_number(cls, v):
        if v:
            # Remove spaces and validate length
            clean_number = v.replace(' ', '')
            if not clean_number.isdigit() or len(clean_number) < 13:
                raise ValueError('Invalid credit card number')
        return v
    
    @validator('card_expiry')
    def validate_expiry(cls, v):
        if v:
            try:
                month, year = v.split('/')
                month, year = int(month), int(year)
                if month < 1 or month > 12:
                    raise ValueError('Invalid expiry month')
                # Add 2000 to year if it's 2-digit
                if year < 100:
                    year += 2000
                from datetime import datetime
                if datetime(year, month, 1) < datetime.now():
                    raise ValueError('Card has expired')
            except:
                raise ValueError('Invalid expiry date format (use MM/YY)')
        return v

class PaymentRequest(BaseModel):
    """Request to process payment for an order"""
    payment_details: PaymentDetailsSchema
    save_payment_method: bool = Field(False, description="Save payment method for future use")
    billing_address_same_as_contact: bool = Field(True, description="Use contact address for billing")

class PaymentResponse(BaseModel):
    """Response from payment processing"""
    success: bool
    order_id: str
    payment_id: Optional[str] = None
    status: str
    message: str
    error: Optional[str] = None
    estimated_completion: Optional[str] = None
    next_steps: Optional[List[str]] = None

class OrderStep(BaseModel):
    """Individual step in order processing"""
    step: str
    status: str  # pending, in_progress, completed, failed
    description: str
    estimated_time: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class OrderStatusResponse(BaseModel):
    """Detailed order status response"""
    order_id: str
    domain: str
    status: str
    payment_status: str
    completion_percentage: int = Field(ge=0, le=100)
    estimated_time_remaining: str
    steps: List[OrderStep]
    created_at: str
    updated_at: str
    error_message: Optional[str] = None
    website_url: Optional[str] = None
    
    # Additional order details
    template_id: Optional[int] = None
    registrar_used: Optional[str] = None
    ssl_certificate: Optional[Dict[str, Any]] = None
    dns_records: Optional[List[Dict[str, str]]] = None

# Additional useful schemas
class TemplateInfo(BaseModel):
    """Website template information"""
    id: int
    name: str
    description: str
    category: str
    preview_url: str
    features: List[str]
    suitable_for: List[str]
    price: Optional[float] = 0.0
    setup_time: str = "5-10 minutes"

class PaymentMethodInfo(BaseModel):
    """Payment method information"""
    id: str
    name: str
    icon: str
    description: str
    processing_time: str = "Instant"
    fees: Optional[str] = None
    supported_currencies: List[str] = ["USD"]

class DomainOrderSummary(BaseModel):
    """Summary of a domain order for listing"""
    order_id: str
    domain: str
    status: str
    amount: float
    currency: str
    created_at: str
    completion_percentage: int
    template_id: Optional[int] = None
    can_cancel: bool = True

# Keep any other schemas you need but make sure no 'regex' parameters exist