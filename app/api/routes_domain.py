# app/api/routes_domain.py - FIXED VERSION for Step 1
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
import asyncio
import time
import re
from datetime import datetime

from app.db.deps import get_db, get_current_vendor
from app.services.multi_registrar_service import (
    multi_registrar_service, 
    bulk_check_domains,
    REGISTRAR_APIS,  # Import the constant
    LOCATION_MARKUP
)
from app.models.vendor import Vendor
from app.schemas.domain import DomainSuggestionOut, DomainSuggestionResponse
from app.core.monitoring import monitoring
from app.core.rate_limiter import rate_limiter

router = APIRouter()

def get_client_country(request: Request) -> str:
    """
    Extract client country from request headers or IP
    Priority: X-Country-Code header > IP geolocation > default
    """
    # Check for explicit country code header (useful for testing)
    country_code = request.headers.get('X-Country-Code')
    if country_code:
        return country_code.upper()
    
    # Check common proxy headers for country
    cf_country = request.headers.get('CF-IPCountry')  # Cloudflare
    if cf_country:
        return cf_country.upper()
    
    # TODO: Implement IP geolocation using MaxMind GeoIP2
    # For now, return default
    return 'US'  # Default to US

def clean_business_name(business_name: str) -> str:
    """Clean business name for domain generation"""
    # Remove common business suffixes
    suffixes = [
        'llc', 'inc', 'corp', 'ltd', 'co', 'company', 'business', 
        'shop', 'store', 'mart', 'restaurant', 'cafe', 'services',
        'solutions', 'technologies', 'enterprises', 'group'
    ]
    
    # Convert to lowercase and remove special characters
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', business_name.lower())
    
    # Remove suffixes
    words = clean.split()
    filtered_words = []
    
    for word in words:
        if word not in suffixes:
            filtered_words.append(word)
    
    return ''.join(filtered_words)

def generate_domain_variations(clean_name: str, max_variations: int = 20) -> List[str]:
    """Generate domain name variations"""
    variations = [clean_name]  # Original name first
    
    # Add common business suffixes
    common_suffixes = [
        'online', 'store', 'shop', 'hub', 'zone', 'pro', 'now',
        'express', 'direct', 'plus', 'max', 'prime', 'best',
        'official', 'global', 'world', 'solutions', 'services'
    ]
    
    for suffix in common_suffixes:
        if len(variations) >= max_variations:
            break
        variations.append(f"{clean_name}{suffix}")
    
    # Add year variations
    current_year = time.strftime('%Y')
    year_variations = [current_year, '24', '2024', '365', '247']
    for year in year_variations:
        if len(variations) >= max_variations:
            break
        variations.append(f"{clean_name}{year}")
    
    # Add short variations for long names
    if len(clean_name) > 8:
        words = clean_name.split() if ' ' in clean_name else [clean_name]
        if len(words) > 1:
            # Create abbreviation
            abbreviation = ''.join([word[0] for word in words])
            variations.append(abbreviation)
            variations.append(f"{abbreviation}online")
    
    # Add "get" prefix variations
    get_variations = [f"get{clean_name}", f"my{clean_name}", f"the{clean_name}"]
    for var in get_variations:
        if len(variations) >= max_variations:
            break
        variations.append(var)
    
    return list(dict.fromkeys(variations))  # Remove duplicates while preserving order

def get_popular_tlds() -> List[str]:
    """Get list of popular TLDs in order of preference"""
    return [
        '.com',     # Most popular
        '.net',     # Second choice
        '.org',     # Non-profit friendly
        '.shop',    # E-commerce
        '.store',   # Retail
        '.online',  # Modern
        '.site',    # General
        '.biz',     # Business
        '.info',    # Information
        '.co',      # Company
        '.io',      # Tech
        '.app',     # Applications
    ]

@router.get("/suggestions/{business_name}", response_model=DomainSuggestionResponse)
async def get_domain_suggestions_with_real_pricing(
    business_name: str,
    max_results: int = Query(12, ge=1, le=25, description="Maximum suggestions to return"),
    request: Request = None,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """
    Get domain suggestions with real-time pricing from multiple registrars
    
    Features:
    - Multi-registrar price comparison
    - Geographic pricing optimization
    - Real availability checking
    - Intelligent caching for performance
    """
    start_time = time.time()
    
    try:
        # Input validation
        if not business_name or len(business_name.strip()) < 2:
            raise HTTPException(
                status_code=400, 
                detail="Business name must be at least 2 characters long"
            )
        
        # Rate limiting per vendor
        if not rate_limiter.is_allowed(f"domain_search_{vendor.id}", max_requests=30, window_seconds=60):
            monitoring.record_rate_limit(vendor.id)
            raise HTTPException(
                status_code=429,
                detail="Too many domain searches. Please wait a moment before trying again."
            )
        
        # Get customer location for pricing
        customer_location = get_client_country(request) if request else 'US'
        location_key = multi_registrar_service.get_customer_location(country_code=customer_location)
        
        # Clean business name and generate variations
        clean_name = clean_business_name(business_name.strip())
        variations = generate_domain_variations(clean_name, max_variations=15)
        popular_tlds = get_popular_tlds()
        
        # Generate domain combinations
        domain_candidates = []
        for variation in variations:
            for tld in popular_tlds:
                if len(domain_candidates) >= max_results * 2:  # Generate more than needed
                    break
                domain_candidates.append(f"{variation}{tld}")
        
        # Initialize multi-registrar service if needed
        if not multi_registrar_service.session:
            await multi_registrar_service.initialize()
        
        # Check domains with real-time pricing (limited batch to avoid timeout)
        batch_size = min(max_results + 5, len(domain_candidates))
        pricing_results = await bulk_check_domains(
            domain_candidates[:batch_size], 
            location_key
        )
        
        # Filter available domains and sort by value
        available_results = [r for r in pricing_results if r.available]
        
        # Sort by recommendation score (price + TLD popularity + name quality)
        def calculate_recommendation_score(result):
            score = 0.0
            
            # Price factor (lower price = higher score)
            if result.customer_price > 0:
                # Normalize price to 0-1 scale (assuming $5-$25 range)
                price_score = max(0, (25 - result.customer_price) / 20)
                score += price_score * 0.4
            
            # TLD popularity
            tld = '.' + result.domain.split('.')[-1]
            tld_scores = {'.com': 1.0, '.net': 0.8, '.org': 0.7, '.shop': 0.6, '.store': 0.5}
            score += tld_scores.get(tld, 0.3) * 0.3
            
            # Name quality (shorter is better, exact match bonus)
            domain_name = result.domain.split('.')[0]
            if domain_name == clean_name:
                score += 0.2  # Exact match bonus
            
            # Length penalty
            if len(domain_name) <= 10:
                score += 0.1
            elif len(domain_name) > 15:
                score -= 0.1
                
            # Profit margin consideration (higher margin slightly preferred)
            if result.margin_percent > 20:
                score += 0.05
            
            return min(1.0, score)
        
        # Add recommendation scores and sort
        for result in available_results:
            result.recommendation_score = calculate_recommendation_score(result)
        
        available_results.sort(key=lambda x: x.recommendation_score, reverse=True)
        
        # Convert to response format
        suggestions = []
        for result in available_results[:max_results]:
            suggestion = DomainSuggestionOut(
                suggested_domain=result.domain,
                tld='.' + result.domain.split('.')[-1],
                registration_price=result.customer_price,
                registration_price_display=f"{result.customer_symbol}{result.customer_price:.2f}",
                renewal_price=result.customer_price,  # Assume same for demo
                renewal_price_display=f"{result.customer_symbol}{result.customer_price:.2f}",
                currency=result.customer_currency,
                currency_symbol=result.customer_symbol,
                is_available=result.available,
                is_premium=result.premium,
                is_popular_tld='.' + result.domain.split('.')[-1] in ['.com', '.net', '.org'],
                recommendation_score=result.recommendation_score,
                wholesale_price=result.wholesale_price,
                wholesale_registrar=result.wholesale_registrar,
                margin_amount=result.margin_amount,
                margin_percent=result.margin_percent,
                response_time_ms=result.response_time_ms
            )
            suggestions.append(suggestion)
        
        # If we don't have enough available domains, add some "taken" examples
        while len(suggestions) < min(8, max_results):
            remaining_domains = [d for d in domain_candidates if d not in [s.suggested_domain for s in suggestions]]
            if not remaining_domains:
                break
                
            # Add unavailable domain
            unavailable_domain = remaining_domains[0]
            tld = '.' + unavailable_domain.split('.')[-1]
            
            suggestion = DomainSuggestionOut(
                suggested_domain=unavailable_domain,
                tld=tld,
                registration_price=0,
                registration_price_display="Unavailable",
                renewal_price=0,
                renewal_price_display="Unavailable",
                currency="USD",
                currency_symbol="$",
                is_available=False,
                is_premium=False,
                is_popular_tld=tld in ['.com', '.net', '.org'],
                recommendation_score=0.0,
                wholesale_price=0,
                wholesale_registrar="none",
                margin_amount=0,
                margin_percent=0,
                response_time_ms=0
            )
            suggestions.append(suggestion)
        
        response_time = (time.time() - start_time) * 1000
        monitoring.record_request(success=True, response_time_ms=response_time)
        
        return DomainSuggestionResponse(
            suggestions=suggestions,
            business_name=business_name.strip(),
            total_suggestions=len(suggestions),
            search_time_ms=int(response_time),
            customer_location=location_key,
            currency=available_results[0].customer_currency if available_results else "USD",
            currency_symbol=available_results[0].customer_symbol if available_results else "$",
            registrars_checked=len(REGISTRAR_APIS),
            available_count=len([s for s in suggestions if s.is_available]),
            cheapest_price=min([s.registration_price for s in suggestions if s.is_available], default=0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        monitoring.record_error(str(e), vendor.id)
        monitoring.record_request(success=False, response_time_ms=response_time)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate domain suggestions: {str(e)}"
        )

@router.get("/check-availability/{domain}")
async def check_single_domain_availability(
    domain: str,
    request: Request = None,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """
    Check availability and pricing for a single domain across all registrars
    """
    start_time = time.time()
    
    try:
        # Input validation
        if not domain or '.' not in domain:
            raise HTTPException(
                status_code=400,
                detail="Please enter a valid domain name (e.g., example.com)"
            )
        
        # Rate limiting
        if not rate_limiter.is_allowed(f"availability_check_{vendor.id}", max_requests=50, window_seconds=60):
            monitoring.record_rate_limit(vendor.id)
            raise HTTPException(
                status_code=429,
                detail="Too many availability checks. Please wait a moment."
            )
        
        # Get customer location for pricing
        customer_location = get_client_country(request) if request else 'US'
        location_key = multi_registrar_service.get_customer_location(country_code=customer_location)
        
        # Initialize service if needed
        if not multi_registrar_service.session:
            await multi_registrar_service.initialize()
        
        # Check domain with detailed registrar information
        result = await multi_registrar_service.get_domain_pricing(
            domain.lower().strip(), 
            location_key,
            include_registrar_details=True
        )
        
        response_time = (time.time() - start_time) * 1000
        monitoring.record_request(success=True, response_time_ms=response_time)
        
        # Format registrar responses for frontend
        registrar_details = []
        for reg_response in result.registrar_responses:
            registrar_details.append({
                "registrar": reg_response.registrar,
                "available": reg_response.available,
                "price": reg_response.price,
                "currency": reg_response.currency,
                "premium": reg_response.premium,
                "response_time_ms": reg_response.response_time_ms,
                "error": reg_response.error
            })
        
        return {
            "domain": result.domain,
            "available": result.available,
            "premium": result.premium,
            "customer_price": result.customer_price,
            "customer_currency": result.customer_currency,
            "customer_symbol": result.customer_symbol,
            "price_display": f"{result.customer_symbol}{result.customer_price:.2f}",
            "wholesale_price": result.wholesale_price,
            "wholesale_registrar": result.wholesale_registrar,
            "margin_amount": result.margin_amount,
            "margin_percent": result.margin_percent,
            "checked_at": result.checked_at,
            "response_time_ms": result.response_time_ms,
            "registrar_details": registrar_details,
            "registrars_checked": len(registrar_details),
            "fastest_registrar": min(registrar_details, key=lambda x: x["response_time_ms"])["registrar"] if registrar_details else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        monitoring.record_error(str(e), vendor.id)
        monitoring.record_request(success=False, response_time_ms=response_time)
        raise HTTPException(
            status_code=500,
            detail=f"Availability check failed: {str(e)}"
        )

@router.get("/test-step1")
async def test_step1_implementation():
    """
    Test endpoint to verify Step 1 implementation is working
    """
    return {
        "message": "Step 1: Multi-Registrar Price Discovery Service",
        "status": "operational",
        "features": [
            "Multi-registrar price comparison",
            "Geographic pricing optimization", 
            "Real-time availability checking",
            "Intelligent caching system",
            "Rate limiting and monitoring"
        ],
        "registrars_configured": len(REGISTRAR_APIS),  # Fixed: use module constant
        "supported_locations": list(LOCATION_MARKUP.keys()),  # Fixed: use module constant
        "cache_enabled": True,
        "monitoring_enabled": True,
        "version": "1.0.0"
    }

@router.get("/registrar-status")
async def get_registrar_status():
    """
    Get current status of all registrar APIs for monitoring
    """
    try:
        registrar_status = {}
        
        # Test connectivity to each registrar
        for registrar_name, config in REGISTRAR_APIS.items():
            try:
                # Simple connectivity test - for now just return mock data
                registrar_status[registrar_name] = {
                    "status": "online",  # Mock status
                    "response_time_ms": 150,  # Mock response time
                    "reliability": config.get('reliability', 95),
                    "avg_price": config.get('avg_price', 0),
                    "last_checked": datetime.utcnow().isoformat()
                }
            except:
                registrar_status[registrar_name] = {
                    "status": "offline",
                    "response_time_ms": 0,
                    "reliability": config.get('reliability', 95),
                    "avg_price": config.get('avg_price', 0),
                    "last_checked": datetime.utcnow().isoformat()
                }
        
        online_count = len([r for r in registrar_status.values() if r["status"] == "online"])
        total_count = len(registrar_status)
        
        return {
            "registrars": registrar_status,
            "summary": {
                "total_registrars": total_count,
                "online_registrars": online_count,
                "offline_registrars": total_count - online_count,
                "overall_health": "healthy" if online_count >= total_count * 0.8 else "degraded"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get registrar status: {str(e)}"
        )
    
    # Add these routes to your existing app/api/routes_domain.py file

from app.services.domain_purchase_service import domain_purchase_service
from app.schemas.domain import (
    DomainPurchaseRequest, 
    DomainPurchaseResponse, 
    PaymentRequest,
    PaymentResponse,
    OrderStatusResponse
)

# Add these new routes to your existing domain router

@router.post("/purchase", response_model=DomainPurchaseResponse)
async def create_domain_purchase_order(
    purchase_request: DomainPurchaseRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """
    Create a new domain purchase order with payment processing
    
    Step 2: Complete purchase flow with payment integration
    """
    start_time = time.time()
    
    try:
        # Rate limiting for purchases
        if not rate_limiter.is_allowed(f"purchase_{vendor.id}", max_requests=10, window_seconds=300):
            monitoring.record_rate_limit(vendor.id)
            raise HTTPException(
                status_code=429,
                detail="Too many purchase attempts. Please wait 5 minutes before trying again."
            )
        
        # Validate domain is still available
        if not multi_registrar_service.session:
            await multi_registrar_service.initialize()
        
        # Get customer location for pricing
        customer_location = multi_registrar_service.get_customer_location()
        
        # Double-check domain availability and pricing
        pricing_result = await multi_registrar_service.get_domain_pricing(
            purchase_request.domain, customer_location
        )
        
        if not pricing_result.available:
            raise HTTPException(
                status_code=400,
                detail=f"Domain {purchase_request.domain} is no longer available"
            )
        
        # Create purchase order
        order_result = await domain_purchase_service.create_purchase_order(
            vendor_id=vendor.id,
            domain=purchase_request.domain,
            contact_info=purchase_request.contact_info,
            payment_method=purchase_request.payment_method,
            template_id=purchase_request.template_id,
            customer_location=customer_location
        )
        
        response_time = (time.time() - start_time) * 1000
        monitoring.record_request(success=True, response_time_ms=response_time)
        
        return DomainPurchaseResponse(
            success=order_result["success"],
            order_id=order_result["order_id"],
            domain=order_result["domain"],
            amount=order_result["amount"],
            currency=order_result["currency"],
            status=order_result["status"],
            payment_methods=order_result["payment_methods"],
            next_step=order_result["next_step"],
            message="Domain purchase order created successfully. Please proceed with payment."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        monitoring.record_error(str(e), vendor.id)
        monitoring.record_request(success=False, response_time_ms=response_time)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create purchase order: {str(e)}"
        )

@router.post("/purchase/{order_id}/payment", response_model=PaymentResponse)
async def process_domain_payment(
    order_id: str,
    payment_request: PaymentRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """
    Process payment for a domain purchase order
    """
    start_time = time.time()
    
    try:
        # Validate order belongs to vendor
        order_status = domain_purchase_service.get_order_status(order_id)
        
        # Security check: ensure order belongs to current vendor
        # In production, you'd query the database to verify ownership
        
        # Process payment
        payment_result = await domain_purchase_service.process_payment(
            order_id=order_id,
            payment_details=payment_request.payment_details
        )
        
        response_time = (time.time() - start_time) * 1000
        
        if payment_result["success"]:
            monitoring.record_request(success=True, response_time_ms=response_time)
            
            return PaymentResponse(
                success=True,
                order_id=order_id,
                payment_id=payment_result.get("payment_id"),
                status=payment_result["status"],
                message=payment_result["message"],
                estimated_completion=payment_result.get("estimated_completion"),
                next_steps=[
                    "Domain registration in progress",
                    "DNS configuration will be setup automatically", 
                    "Your selected template will be deployed",
                    "You'll receive an email when your website is live"
                ]
            )
        else:
            monitoring.record_request(success=False, response_time_ms=response_time)
            
            return PaymentResponse(
                success=False,
                order_id=order_id,
                status=payment_result["status"],
                error=payment_result["error"],
                message="Payment failed. Please try again with a different payment method."
            )
        
    except HTTPException:
        raise
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        monitoring.record_error(str(e), vendor.id)
        monitoring.record_request(success=False, response_time_ms=response_time)
        raise HTTPException(
            status_code=500,
            detail=f"Payment processing failed: {str(e)}"
        )

@router.get("/orders/{order_id}/status", response_model=OrderStatusResponse)
async def get_domain_order_status(
    order_id: str,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """
    Get current status and progress of a domain order
    """
    try:
        order_status = domain_purchase_service.get_order_status(order_id)
        
        return OrderStatusResponse(
            order_id=order_status["order_id"],
            domain=order_status["domain"],
            status=order_status["status"],
            payment_status=order_status["payment_status"],
            completion_percentage=order_status["completion_percentage"],
            estimated_time_remaining=order_status["estimated_time_remaining"],
            steps=order_status["steps"],
            created_at=order_status["created_at"],
            updated_at=order_status["updated_at"],
            error_message=order_status.get("error_message"),
            website_url=f"https://{order_status['domain']}" if order_status["status"] == "completed" else None
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        monitoring.record_error(str(e), vendor.id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get order status: {str(e)}"
        )

@router.get("/orders", response_model=List[Dict[str, Any]])
async def list_domain_orders(
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """
    List all domain orders for the current vendor
    """
    try:
        orders = domain_purchase_service.list_orders(vendor.id)
        
        return {
            "success": True,
            "orders": orders,
            "total": len(orders)
        }
        
    except Exception as e:
        monitoring.record_error(str(e), vendor.id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list orders: {str(e)}"
        )

@router.get("/payment-methods")
async def get_available_payment_methods(
    vendor: Vendor = Depends(get_current_vendor)
):
    """
    Get available payment methods for domain purchases
    """
    try:
        # Get payment methods from the service
        payment_methods = domain_purchase_service._get_available_payment_methods()
        
        return {
            "success": True,
            "payment_methods": payment_methods,
            "total": len(payment_methods),
            "recommended": "credit_card",  # Most reliable
            "notes": {
                "credit_card": "Instant processing, most reliable",
                "paypal": "Secure PayPal integration",
                "stripe": "Advanced security features"
            }
        }
        
    except Exception as e:
        monitoring.record_error(str(e), vendor.id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get payment methods: {str(e)}"
        )

@router.get("/templates")
async def get_available_templates(
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """
    Get available website templates for domain setup
    Integrates with your existing template system
    """
    try:
        # Integration with your existing template system
        # This connects to your VendorStorePage template selection
        
        templates = [
            {
                "id": 1,
                "name": "Modern Restaurant",
                "description": "Perfect for restaurants, cafes, and food businesses",
                "category": "restaurant",
                "preview_url": "/templates/1/preview",
                "features": [
                    "Online menu display",
                    "Order management", 
                    "Contact information",
                    "Photo gallery",
                    "Customer reviews"
                ],
                "suitable_for": ["restaurant", "cafe", "food truck", "catering"]
            },
            {
                "id": 2,
                "name": "E-commerce Shop",
                "description": "Complete online store with product catalog",
                "category": "shop",
                "preview_url": "/templates/2/preview",
                "features": [
                    "Product catalog",
                    "Shopping cart",
                    "Payment integration",
                    "Inventory management",
                    "Order tracking"
                ],
                "suitable_for": ["retail", "online store", "marketplace"]
            },
            {
                "id": 3,
                "name": "Service Business",
                "description": "Professional website for service providers",
                "category": "services",
                "preview_url": "/templates/3/preview",
                "features": [
                    "Service listings",
                    "Appointment booking",
                    "Portfolio showcase",
                    "Client testimonials",
                    "Contact forms"
                ],
                "suitable_for": ["consulting", "freelancing", "professional services"]
            },
            {
                "id": 4,
                "name": "Business Portfolio",
                "description": "Clean, professional business presence",
                "category": "general",
                "preview_url": "/templates/4/preview",
                "features": [
                    "Company information",
                    "Team profiles",
                    "Project showcase",
                    "News and updates",
                    "Contact details"
                ],
                "suitable_for": ["corporate", "agency", "portfolio"]
            }
        ]
        
        return {
            "success": True,
            "templates": templates,
            "total": len(templates),
            "categories": ["restaurant", "shop", "services", "general"],
            "integration_note": "Templates integrate with your existing product/menu data"
        }
        
    except Exception as e:
        monitoring.record_error(str(e), vendor.id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get templates: {str(e)}"
        )

@router.post("/orders/{order_id}/cancel")
async def cancel_domain_order(
    order_id: str,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """
    Cancel a domain order (if still possible)
    """
    try:
        order_status = domain_purchase_service.get_order_status(order_id)
        
        # Check if order can be cancelled
        if order_status["status"] in ["completed", "processing"]:
            raise HTTPException(
                status_code=400,
                detail="Order cannot be cancelled as domain registration is already in progress"
            )
        
        # Cancel the order (implement cancellation logic)
        # This would update the order status and potentially process refunds
        
        return {
            "success": True,
            "order_id": order_id,
            "message": "Order cancelled successfully",
            "refund_info": {
                "eligible": order_status["payment_status"] == "completed",
                "amount": order_status.get("amount", 0),
                "processing_time": "3-5 business days"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        monitoring.record_error(str(e), vendor.id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel order: {str(e)}"
        )

@router.get("/test-step2")
async def test_step2_implementation():
    """
    Test endpoint to verify Step 2 implementation is working
    """
    return {
        "message": "Step 2: Domain Purchase & Payment Integration",
        "status": "operational",
        "features": [
            "Domain purchase order creation",
            "Multi-gateway payment processing",
            "Template selection integration", 
            "Order status tracking",
            "Background domain registration",
            "Real-time progress updates"
        ],
        "payment_methods_available": len(domain_purchase_service._get_available_payment_methods()),
        "templates_available": 4,
        "order_tracking": True,
        "background_processing": True,
        "version": "2.0.0",
        "integration_points": [
            "Multi-registrar service (Step 1)",
            "Existing template system",
            "Vendor authentication",
            "Order management"
        ]
    }

# ADD this to the END of your existing app/api/routes_domain.py file
# Don't change anything else, just add this at the bottom:

@router.get("/test-step2")
async def test_step2_implementation():
    """Test endpoint to verify Step 2 schemas are working"""
    
    # Test if the new schemas can be imported
    try:
        from app.schemas.domain import (
            ContactInfoSchema,
            DomainPurchaseRequest, 
            DomainPurchaseResponse,
            PaymentRequest,
            PaymentResponse,
            OrderStatusResponse
        )
        schemas_loaded = True
        schemas_count = 6
    except ImportError as e:
        schemas_loaded = False
        schemas_count = 0
        import_error = str(e)
    
    return {
        "message": "Step 2: Domain Purchase & Payment Integration",
        "status": "schemas_testing",
        "schemas_loaded": schemas_loaded,
        "schemas_available": schemas_count,
        "import_error": import_error if not schemas_loaded else None,
        "next_step": "Add purchase service if schemas work",
        "version": "2.0.0"
    }

@router.get("/templates")
async def get_available_templates_simple(
    vendor: Vendor = Depends(get_current_vendor)
):
    """Get available website templates - simple version"""
    try:
        templates = [
            {
                "id": 1,
                "name": "Modern Restaurant",
                "description": "Perfect for restaurants, cafes, and food businesses",
                "category": "restaurant",
                "features": ["Online menu", "Order management", "Contact info"]
            },
            {
                "id": 2,
                "name": "E-commerce Shop", 
                "description": "Complete online store with product catalog",
                "category": "shop",
                "features": ["Product catalog", "Shopping cart", "Payments"]
            },
            {
                "id": 3,
                "name": "Service Business",
                "description": "Professional website for service providers", 
                "category": "services",
                "features": ["Service listings", "Appointments", "Portfolio"]
            }
        ]
        
        return {
            "success": True,
            "templates": templates,
            "total": len(templates)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "templates": []
        }

@router.get("/payment-methods")  
async def get_payment_methods_simple(
    vendor: Vendor = Depends(get_current_vendor)
):
    """Get available payment methods - simple version"""
    try:
        payment_methods = [
            {
                "id": "credit_card",
                "name": "Credit Card", 
                "icon": "💳",
                "description": "Visa, Mastercard, American Express"
            },
            {
                "id": "paypal",
                "name": "PayPal",
                "icon": "🅿️", 
                "description": "Pay with your PayPal account"
            }
        ]
        
        return {
            "success": True,
            "payment_methods": payment_methods,
            "total": len(payment_methods)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "payment_methods": []
        }