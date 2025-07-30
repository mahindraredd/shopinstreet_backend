import time
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger("monitoring")

class EnterpriseMonitoring:
    """Real-time monitoring for enterprise systems"""
    
    def __init__(self):
        self.metrics = {
            "requests_total": 0,
            "requests_successful": 0,
            "requests_failed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "rate_limits_hit": 0,
            "average_response_time": 0,
            "last_error": None
        }
    
    def record_request(self, success: bool, response_time_ms: float, from_cache: bool = False):
        """Record API request metrics"""
        self.metrics["requests_total"] += 1
        
        if success:
            self.metrics["requests_successful"] += 1
        else:
            self.metrics["requests_failed"] += 1
        
        if from_cache:
            self.metrics["cache_hits"] += 1
        else:
            self.metrics["cache_misses"] += 1
        
        # Update average response time
        current_avg = self.metrics["average_response_time"]
        total_requests = self.metrics["requests_total"]
        self.metrics["average_response_time"] = (
            (current_avg * (total_requests - 1) + response_time_ms) / total_requests
        )
    
    def record_rate_limit(self, vendor_id: int):
        """Record rate limit hit"""
        self.metrics["rate_limits_hit"] += 1
        logger.warning(f"Rate limit hit for vendor {vendor_id}")
    
    def record_error(self, error: str, vendor_id: int = None):
        """Record system error"""
        self.metrics["last_error"] = {
            "error": error,
            "vendor_id": vendor_id,
            "timestamp": datetime.now().isoformat()
        }
        logger.error(f"System error: {error} (vendor: {vendor_id})")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current system health"""
        total_requests = self.metrics["requests_total"]
        
        if total_requests == 0:
            success_rate = 100.0
        else:
            success_rate = (self.metrics["requests_successful"] / total_requests) * 100
        
        cache_hit_rate = 0.0
        if self.metrics["cache_hits"] + self.metrics["cache_misses"] > 0:
            cache_hit_rate = (
                self.metrics["cache_hits"] / 
                (self.metrics["cache_hits"] + self.metrics["cache_misses"])
            ) * 100
        
        # Determine health status
        if success_rate >= 99 and self.metrics["average_response_time"] < 500:
            status = "EXCELLENT"
        elif success_rate >= 95 and self.metrics["average_response_time"] < 1000:
            status = "GOOD"
        elif success_rate >= 90:
            status = "WARNING"
        else:
            status = "CRITICAL"
        
        return {
            "status": status,
            "success_rate": round(success_rate, 2),
            "cache_hit_rate": round(cache_hit_rate, 2),
            "average_response_time_ms": round(self.metrics["average_response_time"], 2),
            "total_requests": total_requests,
            "rate_limits_hit": self.metrics["rate_limits_hit"],
            "last_error": self.metrics["last_error"],
            "timestamp": datetime.now().isoformat()
        }

# Global monitoring instance
monitoring = EnterpriseMonitoring()