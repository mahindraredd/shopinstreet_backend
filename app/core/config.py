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
    
    class Config:
        env_file = ".env"
        case_sensitive = False  # Allow lowercase env vars
        extra = "ignore"        # 👈 This ignores extra fields instead of erroring

settings = Settings()