from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, logger
from sqlalchemy.orm import Session
from typing import List, Dict

from app.db.deps import get_db, get_current_vendor
from app.services.domain_config import DomainConfig
from app.services.indian_domain_service import IndianDomainService
from app.models.vendor import Vendor
from app.models.domain import DomainOrder, VendorDomain
from app.schemas.domain import (
    DomainSuggestionResponse, DomainPurchaseRequest, DomainPurchaseResponse,
    OrderStatusResponse, ExistingDomainRequest, VendorDomainOut,
)

router = APIRouter()

# Initialize domain service
domain_service = IndianDomainService()

@router.get("/search/{business_name}", response_model=DomainSuggestionResponse)
async def search_indian_domains(
    business_name: str,
    max_results: int = Query(12, ge=1, le=20),
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Search for available domains with Indian TLD pricing in INR"""
    try:
        if not business_name or len(business_name.strip()) < 2:
            raise HTTPException(status_code=400, detail="Business name must be at least 2 characters")
        
        # Generate suggestions with Indian TLDs and INR pricing
        suggestions = domain_service.generate_indian_domain_suggestions(
            business_name=business_name.strip(),
            max_suggestions=max_results
        )
        
        # Check availability for top suggestions
        if suggestions:
            top_domains = [s["suggested_domain"] for s in suggestions[:5]]
            availability_results = await domain_service.check_bulk_domain_availability(top_domains)
            
            # Update availability status
            for suggestion in suggestions:
                domain_name = suggestion["suggested_domain"]
                if domain_name in availability_results:
                    suggestion["is_available"] = availability_results[domain_name].get("available", True)
        
        return DomainSuggestionResponse(
            suggestions=suggestions,
            business_name=business_name.strip(),
            total_suggestions=len(suggestions)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/purchase", response_model=DomainPurchaseResponse)
async def purchase_domain(
    purchase_data: DomainPurchaseRequest,
    background_tasks: BackgroundTasks,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Purchase domain with template selection and automatic hosting"""
    try:
        # Create domain purchase order
        order_result = await domain_service.create_domain_purchase_order(
            db=db,
            vendor_id=vendor.id,
            domain_name=purchase_data.domain_name,
            template_id=purchase_data.template_id,
            contact_info=purchase_data.contact_info.dict(),
            payment_method=purchase_data.payment_method
        )
        
        if not order_result["success"]:
            return DomainPurchaseResponse(
                success=False,
                message="Failed to create order",
                error=order_result["error"]
            )
        
        return DomainPurchaseResponse(
            success=True,
            order_id=order_result["order_id"],
            order_number=order_result["order_number"],
            domain_name=order_result["domain_name"],
            total_amount_inr=order_result["total_amount_inr"],
            registrar=order_result["registrar"],
            message="Domain purchase order created successfully"
        )
    
    except Exception as e:
        return DomainPurchaseResponse(
            success=False,
            message="Purchase failed",
            error=str(e)
        )

@router.post("/confirm-payment/{order_id}")
async def confirm_payment(
    order_id: int,
    payment_data: Dict,
    background_tasks: BackgroundTasks,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Confirm payment and start domain processing"""
    try:
        # Get order
        order = db.query(DomainOrder).filter(
            DomainOrder.id == order_id,
            DomainOrder.vendor_id == vendor.id
        ).first()
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # For testing, assume payment is always verified
        # In production, verify with actual payment gateway
        payment_verified = True
        
        if payment_verified:
            # Update order status
            from app.models.domain import PaymentStatus, DomainStatus
            order.payment_status = PaymentStatus.COMPLETED
            order.order_status = DomainStatus.PURCHASED
            order.completion_percentage = 5
            order.current_step = "payment_confirmed"
            order.payment_confirmed_at = datetime.utcnow()
            db.commit()
            
            # Start background processing
            background_tasks.add_task(
                domain_service.process_domain_order_background,
                order_id,
                db
            )
            
            return {
                "success": True,
                "order_id": order_id,
                "status": "processing_started",
                "message": "Payment confirmed. Domain registration and hosting setup in progress.",
                "estimated_time": "24-48 hours",
                "tracking_url": f"/api/domains/status/{order_id}"
            }
        else:
            raise HTTPException(status_code=400, detail="Payment verification failed")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment confirmation failed: {str(e)}")

@router.get("/status/{order_id}", response_model=OrderStatusResponse)
async def get_order_status(
    order_id: int,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Get real-time order processing status"""
    try:
        # Verify order belongs to vendor
        order = db.query(DomainOrder).filter(
            DomainOrder.id == order_id,
            DomainOrder.vendor_id == vendor.id
        ).first()
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        status = domain_service.get_order_status(order_id, db)
        
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        
        return OrderStatusResponse(**status)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.get("/orders")
async def get_vendor_orders(
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Get all domain orders for vendor"""
    try:
        orders = db.query(DomainOrder).filter(
            DomainOrder.vendor_id == vendor.id
        ).order_by(DomainOrder.created_at.desc()).all()
        
        order_list = []
        for order in orders:
            order_info = {
                "id": order.id,
                "order_number": order.order_number,
                "domain_name": order.domain_name,
                "status": order.order_status.value,
                "completion_percentage": order.completion_percentage,
                "current_step": order.current_step,
                "total_amount_inr": order.total_amount_inr,
                "payment_status": order.payment_status.value,
                "registrar": order.selected_registrar.value if order.selected_registrar else "godaddy",
                "created_at": order.created_at.isoformat() if order.created_at else None
            }
            
            if order.completed_at:
                order_info["completed_at"] = order.completed_at.isoformat()
                order_info["website_url"] = f"https://{order.domain_name}"
            
            if order.error_message:
                order_info["error_message"] = order.error_message
            
            order_list.append(order_info)
        
        return {
            "success": True,
            "orders": order_list,
            "total": len(order_list)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get orders: {str(e)}")

@router.get("/my-domains")
async def get_vendor_domains(
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Get all active domains for vendor"""
    try:
        domains = db.query(VendorDomain).filter(
            VendorDomain.vendor_id == vendor.id
        ).order_by(VendorDomain.created_at.desc()).all()
        
        domain_list = []
        for domain in domains:
            domain_info = VendorDomainOut(
                id=domain.id,
                domain_name=domain.domain_name,
                type=domain.domain_type.value,
                status=domain.status.value,
                template_id=domain.template_id,
                ssl_enabled=domain.ssl_enabled,
                hosting_active=domain.hosting_active,
                purchase_price_inr=domain.purchase_price_inr,
                renewal_price_inr=domain.renewal_price_inr,
                registrar=domain.registrar.value if domain.registrar else None,
                expiry_date=domain.expiry_date.isoformat() if domain.expiry_date else None,
                created_at=domain.created_at.isoformat() if domain.created_at else "",
                website_url=f"https://{domain.domain_name}" if domain.ssl_enabled else f"http://{domain.domain_name}"
            )
            domain_list.append(domain_info.dict())
        
        return {
            "success": True,
            "domains": domain_list,
            "total": len(domain_list)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get domains: {str(e)}")

@router.post("/connect-existing")
async def connect_existing_domain(
    domain_data: ExistingDomainRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Connect existing domain to Vision platform (simplified version)"""
    try:
        # Check if domain already exists
        existing = db.query(VendorDomain).filter(
            VendorDomain.domain_name == domain_data.domain_name
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Domain already connected")
        
        # Create domain record (simplified - no verification for now)
        from app.models.domain import DomainStatus, DomainType
        vendor_domain = VendorDomain(
            vendor_id=vendor.id,
            domain_name=domain_data.domain_name,
            domain_type=DomainType.CUSTOM,
            status=DomainStatus.VERIFICATION_PENDING,
            template_id=domain_data.template_id,
            ssl_enabled=False,
            dns_configured=False,
            hosting_active=False
        )
        
        db.add(vendor_domain)
        db.commit()
        db.refresh(vendor_domain)
        
        return {
            "success": True,
            "domain_id": vendor_domain.id,
            "message": f"Domain {domain_data.domain_name} connection initiated",
            "next_steps": [
                "1. Verify domain ownership via DNS",
                "2. Update nameservers to Vision hosting",
                "3. Deploy selected template automatically"
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Domain connection failed: {str(e)}")

@router.get("/templates")
async def get_available_templates(
    vendor: Vendor = Depends(get_current_vendor)
):
    """Get available templates for domain setup"""
    try:
        # Integration with existing template system
        templates = [
            {
                "id": 1,
                "name": "Modern Business",
                "description": "Perfect for professional services and consultancies",
                "category": "business",
                "preview_url": "/templates/1/preview",
                "features": ["Professional design", "Contact forms", "Service listings"],
                "suitable_for": ["Consultancies", "Agencies", "Professional Services"]
            },
            {
                "id": 2,
                "name": "E-commerce Store", 
                "description": "Complete online store with product catalog and cart",
                "category": "ecommerce",
                "preview_url": "/templates/2/preview",
                "features": ["Product catalog", "Shopping cart", "Payment integration"],
                "suitable_for": ["Retail", "Online Stores", "Product Sales"]
            },
            {
                "id": 3,
                "name": "Restaurant & Food",
                "description": "Perfect for restaurants, cafes, and food businesses",
                "category": "restaurant",
                "preview_url": "/templates/3/preview", 
                "features": ["Menu display", "Online ordering", "Location info"],
                "suitable_for": ["Restaurants", "Cafes", "Food Delivery"]
            },
            {
                "id": 4,
                "name": "Portfolio Showcase",
                "description": "Showcase your work and attract clients",
                "category": "portfolio",
                "preview_url": "/templates/4/preview",
                "features": ["Portfolio gallery", "About section", "Contact forms"],
                "suitable_for": ["Freelancers", "Artists", "Photographers"]
            }
        ]
        
        return {
            "success": True,
            "templates": templates,
            "total": len(templates),
            "note": "Templates will be automatically deployed to your domain after purchase"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")

@router.get("/health")
async def domain_service_health():
    """Health check for domain service"""
    return {
        "service": "Indian Domain Service",
        "status": "operational",
        "version": "1.0.0",
        "features": [
            "Indian TLD support (.in, .co.in, etc.)",
            "INR pricing and payment",
            "GoDaddy integration",
            "Automatic template deployment",
            "Real-time order tracking",
            "Background processing",
            "SSL and hosting included"
        ],
        "market": "India",
        "currency": "INR",
        "supported_tlds": ["com", "in", "co.in", "net.in", "org.in", "shop", "store", "co", "online", "site"],
        "registrar": "godaddy",
        "using_mock": domain_service.using_mock
    }

    # Add these endpoints to your app/api/routes_domain.py

@router.get("/search-real-pricing/{business_name}")
async def search_domains_with_real_pricing(
    business_name: str,
    max_results: int = Query(12, ge=1, le=20),
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Search for domains with real-time GoDaddy pricing"""
    
    try:
        if not business_name or len(business_name.strip()) < 2:
            raise HTTPException(status_code=400, detail="Business name must be at least 2 characters")
        
        # Generate suggestions with real pricing
        result = await domain_service.generate_domain_suggestions_with_real_pricing(
            business_name=business_name.strip(),
            max_suggestions=max_results
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Real pricing search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/real-price/{domain}")
async def get_real_domain_price(
    domain: str,
    vendor: Vendor = Depends(get_current_vendor)
):
    """Get real-time price for a specific domain"""
    
    try:
        from app.services.real_pricing_service import RealPricingService
        
        # Validate domain format
        if not domain or '.' not in domain:
            raise HTTPException(status_code=400, detail="Invalid domain format")
        
        pricing_service = RealPricingService()
        result = pricing_service.get_real_domain_price(domain.lower().strip())
        
        if not result.get("success", True):
            raise HTTPException(status_code=400, detail=result.get("error", "Price check failed"))
        
        return {
            "success": True,
            "domain": domain,
            "pricing": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Real price check failed for {domain}: {e}")
        raise HTTPException(status_code=500, detail=f"Price check failed: {str(e)}")

@router.post("/bulk-real-pricing")
async def get_bulk_real_pricing(
    domains: List[str],
    vendor: Vendor = Depends(get_current_vendor)
):
    """Get real-time pricing for multiple domains"""
    
    try:
        from app.services.real_pricing_service import RealPricingService
        
        if not domains or len(domains) == 0:
            raise HTTPException(status_code=400, detail="No domains provided")
        
        if len(domains) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 domains per request")
        
        # Clean domain list
        clean_domains = [d.lower().strip() for d in domains if d and '.' in d]
        
        if not clean_domains:
            raise HTTPException(status_code=400, detail="No valid domains provided")
        
        pricing_service = RealPricingService()
        results = await pricing_service.get_bulk_real_prices(clean_domains)
        
        # Calculate summary statistics
        total_domains = len(results)
        available_domains = sum(1 for r in results.values() if r.get("available", False))
        real_prices = sum(1 for r in results.values() if r.get("source") == "godaddy_api")
        
        return {
            "success": True,
            "results": results,
            "summary": {
                "total_domains": total_domains,
                "available_domains": available_domains,
                "real_api_prices": real_prices,
                "accuracy_percentage": round((real_prices / total_domains) * 100, 1)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk pricing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk pricing failed: {str(e)}")

@router.get("/pricing-comparison/{domain}")
async def compare_static_vs_real_pricing(
    domain: str,
    vendor: Vendor = Depends(get_current_vendor)
):
    """Compare static pricing vs real GoDaddy pricing for analysis"""
    
    try:
        from app.services.real_pricing_service import RealPricingService
        
        # Get static price
        tld = domain.split('.')[-1]
        static_config = DomainConfig.get_tld_pricing(tld)
        static_price = static_config["price_inr"]
        
        # Get real price
        pricing_service = RealPricingService()
        real_price_info = pricing_service.get_real_domain_price(domain)
        
        comparison = {
            "domain": domain,
            "static_pricing": {
                "price_inr": static_price,
                "source": "domain_config.py",
                "last_updated": "static"
            },
            "real_pricing": real_price_info,
            "comparison": {}
        }
        
        if real_price_info.get("success") and real_price_info.get("source") == "godaddy_api":
            real_price = real_price_info["price_inr"]
            difference = real_price - static_price
            percentage_diff = (difference / static_price) * 100
            
            comparison["comparison"] = {
                "price_difference_inr": round(difference, 2),
                "percentage_difference": round(percentage_diff, 1),
                "static_is_higher": static_price > real_price,
                "real_is_higher": real_price > static_price,
                "recommendation": (
                    "Static price too low - risk of loss" if static_price < real_price 
                    else "Static price higher - may lose customers" if static_price > real_price * 1.2
                    else "Static price reasonable"
                )
            }
        
        return comparison
        
    except Exception as e:
        logger.error(f"Pricing comparison failed: {e}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")

@router.get("/pricing-health")
async def check_pricing_service_health():
    """Health check for real pricing service"""
    
    try:
        from app.services.real_pricing_service import RealPricingService
        
        pricing_service = RealPricingService()
        
        # Test with a known domain
        test_result = pricing_service.get_real_domain_price("example.com")
        
        return {
            "service": "Real Pricing Service",
            "status": "operational",
            "godaddy_api": "connected" if test_result.get("source") == "godaddy_api" else "fallback",
            "exchange_rate": pricing_service.exchange_rate,
            "markup_percentage": pricing_service.markup_percentage * 100,
            "last_test": datetime.now().isoformat(),
            "test_domain_result": test_result
        }
        
    except Exception as e:
        return {
            "service": "Real Pricing Service", 
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }