# app/core/config.py - Updated with Business Profile Settings

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Existing required settings
    allowed_image_types: str = "image/jpeg,image/png,image/webp" 

    SECRET_KEY: str
    DATABASE_URL: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"
    AWS_ACCESS_KEY_ID: str = "AKIATFBRXOUMPPTNYCKG"
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-2"
    AWS_BUCKET_NAME: str
    
    # AI settings (optional)
    OPENAI_API_KEY: Optional[str] = None
    AI_MODEL: str = "gpt-4o"
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # NEW: Business Profile Settings
    BANKING_ENCRYPTION_KEY: Optional[str] = None  # 👈 Add this
    ENVIRONMENT: str = "development"              # 👈 Add this
    
    # NEW: Business Profile Features
    ENABLE_BANKING_ENCRYPTION: bool = True
    ENABLE_COMPLIANCE_TRACKING: bool = True
    ENABLE_RISK_SCORING: bool = True
    PROFILE_COMPLETION_THRESHOLD: int = 80  # Profile considered complete at 80%
    
    # NEW: Security Settings
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15
    PASSWORD_MIN_LENGTH: int = 8
    
    # NEW: Business Rules
    DEFAULT_CURRENCY: str = "USD"
    DEFAULT_TIMEZONE: str = "UTC"
    SUPPORTED_COUNTRIES: str = "India,Canada,United States"

    # Indian Payment Gateways
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    
    # PayU (Alternative Indian Payment Gateway)
    PAYU_MERCHANT_ID: Optional[str] = None
    PAYU_MERCHANT_KEY: Optional[str] = None
    PAYU_MERCHANT_SALT: Optional[str] = None
    
    # Domain Registrar APIs (GoDaddy & Namecheap Only)
    GODADDY_API_KEY: Optional[str] = None
    GODADDY_API_SECRET: Optional[str] = None
    GODADDY_ENVIRONMENT: str = "OTE"  # OTE for testing, PRODUCTION for live
    
    NAMECHEAP_API_KEY: Optional[str] = None
    NAMECHEAP_USERNAME: Optional[str] = None
    NAMECHEAP_ENVIRONMENT: str = "sandbox"  # sandbox for testing, production for live
    
    # Domain Service Settings
    DOMAIN_DEFAULT_NAMESERVERS: str = "ns1.vision.com,ns2.vision.com"
    DOMAIN_HOSTING_IP: str = "103.21.244.0"  # Your hosting server IP
    DOMAIN_SETUP_EMAIL: str = "domains@vision.com"
    
    # Currency Exchange (USD to INR conversion)
    EXCHANGE_RATE_API_KEY: Optional[str] = None
    USD_TO_INR_RATE: float = 83.0  # Fallback rate, will be updated via API
    
    # Background Processing (Optional - for production scale)
    REDIS_URL: Optional[str] = None
    CELERY_BROKER_URL: Optional[str] = None
    
    # Domain Processing Settings
    DOMAIN_ORDER_TIMEOUT_MINUTES: int = 30
    DOMAIN_MAX_RETRIES: int = 3
    DOMAIN_PROCESSING_DELAY_SECONDS: int = 5
    
    
    
    class Config:
        env_file = ".env"
        case_sensitive = False  # Allow lowercase env vars
        extra = "ignore"        # 👈 This ignores extra fields instead of erroring

settings = Settings()