# Replace your entire app/core/config.py with this:

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Required existing settings

    allowed_image_types: str = "image/jpeg,image/png,image/webp" 

    SECRET_KEY: str
    DATABASE_URL: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"
    AWS_ACCESS_KEY_ID: str = "AKIATFBRXOUMPPTNYCKG"
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-2"
    AWS_BUCKET_NAME: str
    
    # NEW: AI settings (optional)
    OPENAI_API_KEY: Optional[str] = None
    AI_MODEL: str = "gpt-4o"
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    class Config:
        env_file = ".env"

settings = Settings()