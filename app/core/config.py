
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str
    DATABASE_URL: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"
    AWS_ACCESS_KEY_ID: str = "AKIATFBRXOUMK5PUICPZ"
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-2"  # Example: us-east-1
    AWS_BUCKET_NAME: str

    class Config:
        env_file = ".env"  # tells Pydantic where to load environment variables

settings = Settings()
# Settings instance
settings = Settings()


