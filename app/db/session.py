from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from app.core.config import settings
import logging

logger = logging.getLogger("database")

# Enterprise-grade engine with connection pooling for millions of users
engine = create_engine(
    settings.DATABASE_URL,
    # Connection pooling configuration
    poolclass=QueuePool,
    pool_size=20,                    # Base connections
    max_overflow=50,                 # Additional connections under load  
    pool_pre_ping=True,              # Validate connections
    pool_recycle=3600,               # Recycle every hour
    echo=False,                      # Set True only for debugging
    
    # Performance optimizations
    connect_args={
        "options": "-c timezone=utc",
        "application_name": "vendor_analytics_enterprise"
    }
)

# Add connection monitoring
@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    logger.info("Enterprise DB connection established")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()