from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.deps import get_db, get_current_vendor
from app.models.vendor import Vendor
from app.core.cache import cache
from app.core.rate_limiter import rate_limiter
from app.core.monitoring import monitoring
import time

router = APIRouter()

@router.get("/health")
def get_system_health():
    """Enterprise system health check"""
    return monitoring.get_health_status()

@router.get("/test")
def test_analytics(
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    start_time = time.time()
    
    try:
        result = {
            "message": "Enterprise Analytics API with Monitoring",
            "vendor_id": vendor.id,
            "status": "success",
            "features": ["Redis Cache", "Rate Limiting", "Real-time Monitoring"]
        }
        
        response_time = (time.time() - start_time) * 1000
        monitoring.record_request(success=True, response_time_ms=response_time)
        
        return result
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        monitoring.record_error(str(e), vendor.id)
        monitoring.record_request(success=False, response_time_ms=response_time)
        raise

@router.get("/overview")
def get_basic_overview(
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    start_time = time.time()
    
    try:
        # Rate limiting
        if not rate_limiter.is_allowed(f"vendor_{vendor.id}", max_requests=10, window_seconds=60):
            monitoring.record_rate_limit(vendor.id)
            raise HTTPException(
                status_code=429, 
                detail="Rate limit exceeded. Maximum 10 requests per minute."
            )
        
        # Check cache first
        cache_key = f"overview_vendor_{vendor.id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            cached_data["from_cache"] = True
            response_time = (time.time() - start_time) * 1000
            monitoring.record_request(success=True, response_time_ms=response_time, from_cache=True)
            return cached_data
        
        # Database query
        from app.models.order import Order
        from sqlalchemy import func
        
        total_orders = db.query(Order).filter(Order.vendor_id == vendor.id).count()
        total_revenue = db.query(func.sum(Order.total_amount)).filter(
            Order.vendor_id == vendor.id
        ).scalar() or 0.0
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0.0
        
        result = {
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "average_order_value": round(avg_order_value, 2),
            "vendor_id": vendor.id,
            "from_cache": False
        }
        
        # Cache the result
        cache.set(cache_key, result, ttl=300)
        
        # Record metrics
        response_time = (time.time() - start_time) * 1000
        monitoring.record_request(success=True, response_time_ms=response_time, from_cache=False)
        
        return result
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions (like rate limiting)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        monitoring.record_error(str(e), vendor.id)
        monitoring.record_request(success=False, response_time_ms=response_time)
        raise HTTPException(status_code=500, detail="Internal server error")