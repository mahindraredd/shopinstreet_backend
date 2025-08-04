import redis
import json
import logging
from typing import Any, Optional
from app.core.config import settings

logger = logging.getLogger("cache")

class EnterpriseCache:
    """Enterprise Redis cache for millions of users"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True,
            max_connections=20,
            retry_on_timeout=True
        )
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.redis_client.get(f"analytics:{key}")
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache GET failed for {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL (default 5 minutes)"""
        try:
            serialized = json.dumps(value, default=str)
            return self.redis_client.setex(f"analytics:{key}", ttl, serialized)
        except Exception as e:
            logger.error(f"Cache SET failed for {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            return bool(self.redis_client.delete(f"analytics:{key}"))
        except Exception as e:
            logger.warning(f"Cache DELETE failed for {key}: {e}")
            return False

# Global cache instance
cache = EnterpriseCache()