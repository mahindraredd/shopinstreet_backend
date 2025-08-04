import time
from typing import Dict
import redis

class EnterpriseRateLimiter:
    """Sliding window rate limiter for millions of users"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host='localhost', port=6379, db=1, decode_responses=True
        )
    
    def is_allowed(self, identifier: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
        """
        Check if request is allowed using sliding window algorithm
        Returns True if allowed, False if rate limited
        """
        current_time = int(time.time())
        window_start = current_time - window_seconds
        
        # Redis key for this identifier
        key = f"rate_limit:{identifier}"
        
        try:
            # Remove old entries outside the window
            self.redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            current_requests = self.redis_client.zcard(key)
            
            if current_requests >= max_requests:
                return False  # Rate limited
            
            # Add current request
            self.redis_client.zadd(key, {str(current_time): current_time})
            
            # Set expiry on the key
            self.redis_client.expire(key, window_seconds)
            
            return True  # Request allowed
            
        except Exception as e:
            print(f"Rate limiter error: {e}")
            return True  # Allow request if Redis fails (fail-open)

# Global rate limiter instance
rate_limiter = EnterpriseRateLimiter()