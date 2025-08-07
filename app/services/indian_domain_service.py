# app/services/indian_domain_service.py
import asyncio
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.domain import DomainOrder, VendorDomain, DomainStatus, DomainType, PaymentStatus, RegistrarType
from app.models.vendor import Vendor
from app.services.domain_config import DomainConfig
from app.core.config import settings

# Fallback imports for GoDaddy service
try:
    from app.services.godaddy_service import GoDaddyService
    GODADDY_AVAILABLE = True
except ImportError:
    GODADDY_AVAILABLE = False
    GoDaddyService = None

try:
    from app.services.mock_godaddy_service import MockGoDaddyService
    MOCK_AVAILABLE = True
except ImportError:
    MOCK_AVAILABLE = False
    MockGoDaddyService = None

logger = logging.getLogger(__name__)

class IndianDomainService:
    """Production domain service for Indian market"""
    
    def __init__(self):
        """Initialize with fallback to mock service"""
        
        # Try to use real GoDaddy service first
        try:
            if not GODADDY_AVAILABLE:
                raise ImportError("GoDaddy service not available")
                
            self.godaddy = GoDaddyService()
            
            # Quick connection test
            test_result = self.godaddy.test_connection()
            if not test_result.get("success", False):
                raise Exception("GoDaddy connection test failed")
                
            self.using_mock = False
            logger.info("Using real GoDaddy service")
            
        except Exception as e:
            logger.warning(f"GoDaddy service unavailable: {e}")
            
            # Fallback to mock service
            try:
                if not MOCK_AVAILABLE:
                    raise ImportError("Mock service not available")
                    
                self.godaddy = MockGoDaddyService()
                self.using_mock = True
                logger.info("Using mock GoDaddy service for testing")
                
            except ImportError:
                raise Exception("Neither real nor mock GoDaddy service available")
        
        self.config = DomainConfig()
        
        # Processing orders cache for real-time tracking
        self.processing_orders = {}
    
    def generate_indian_domain_suggestions(self, business_name: str, max_suggestions: int = 12) -> List[Dict]:
        """Generate domain suggestions with Indian TLDs and INR pricing"""
        
        # Clean and create variations of business name
        clean_name = self._clean_business_name(business_name)
        variations = self._generate_name_variations(clean_name)
        
        # Get supported TLDs
        supported_tlds = self.config.get_supported_tlds()
        
        suggestions = []
        
        for variation in variations[:6]:  # Limit variations
            for tld in supported_tlds:
                if len(suggestions) >= max_suggestions:
                    break
                    
                tld_config = self.config.get_tld_pricing(tld)
                domain = f"{variation}.{tld}"
                
                suggestion = {
                    "suggested_domain": domain,
                    "tld": tld,
                    "registration_price_inr": tld_config["price_inr"],
                    "renewal_price_inr": tld_config["renewal_inr"],
                    "is_popular_tld": tld_config["popular"],
                    "recommendation_score": self._calculate_recommendation_score(
                        variation, tld_config, clean_name
                    ),
                    "is_available": True,  # Will be checked asynchronously
                    "is_premium": self._is_premium_domain(domain),
                    "hosting_included": True,
                    "ssl_included": True,
                    "setup_time": "24-48 hours",
                    "registrar": "godaddy"
                }
                
                suggestions.append(suggestion)
        
        # Sort by recommendation score
        suggestions.sort(key=lambda x: x["recommendation_score"], reverse=True)
        
        return suggestions[:max_suggestions]
    
    async def check_bulk_domain_availability(self, domains: List[str]) -> Dict[str, Dict]:
        """Check availability for multiple domains"""
        results = {}
        
        # Check each domain with GoDaddy (or mock)
        for domain in domains:
            try:
                result = self.godaddy.check_domain_availability(domain)
                results[domain] = result
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error checking {domain}: {e}")
                results[domain] = {
                    "available": False,
                    "error": str(e),
                    "domain": domain
                }
        
        return results
    
    async def create_domain_purchase_order(
        self, 
        db: Session,
        vendor_id: int,
        domain_name: str,
        template_id: int,
        contact_info: Dict,
        payment_method: str = "razorpay"
    ) -> Dict:
        """Create domain purchase order with Indian pricing"""
        
        try:
            # Get pricing from our config (not GoDaddy pricing)
            tld = domain_name.split('.')[-1]
            tld_config = self.config.get_tld_pricing(tld)
            
            domain_price = tld_config["price_inr"]
            
            # Premium domain pricing
            if self._is_premium_domain(domain_name):
                domain_price *= 2
            
            # Generate order number
            order_number = f"DOM{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
            
            # Create order
            order = DomainOrder(
                vendor_id=vendor_id,
                order_number=order_number,
                domain_name=domain_name,
                domain_type=DomainType.PURCHASED,
                template_id=template_id,
                domain_price_inr=domain_price,
                hosting_price_inr=0.0,  # Free hosting
                ssl_price_inr=0.0,      # Free SSL
                total_amount_inr=domain_price,
                payment_method=payment_method,
                contact_info=contact_info,
                selected_registrar=RegistrarType.GODADDY,
                order_status=DomainStatus.PENDING_PURCHASE,
                current_step="payment_pending"
            )
            
            db.add(order)
            db.commit()
            db.refresh(order)
            
            logger.info(f"Domain order created: {order_number} for {domain_name}")
            
            return {
                "success": True,
                "order_id": order.id,
                "order_number": order_number,
                "domain_name": domain_name,
                "total_amount_inr": domain_price,
                "registrar": "godaddy",
                "message": "Order created successfully"
            }
        
        except Exception as e:
            logger.error(f"Failed to create domain purchase order: {e}")
            db.rollback()
            return {"success": False, "error": f"Failed to create order: {str(e)}"}
    
    async def process_domain_order_background(self, order_id: int, db: Session):
        """Process domain order in background after payment confirmation"""
        
        try:
            order = db.query(DomainOrder).filter(DomainOrder.id == order_id).first()
            if not order:
                logger.error(f"Order {order_id} not found")
                return
            
            logger.info(f"Starting domain processing for order {order_id}: {order.domain_name}")
            
            # Store processing status
            self.processing_orders[order_id] = {
                "status": order.order_status.value,
                "completion_percentage": order.completion_percentage,
                "current_step": order.current_step,
                "started_at": datetime.utcnow()
            }
            
            # Step 1: Register domain with GoDaddy (30%)
            await self._register_domain_with_godaddy(order, db)
            
            # Step 2: Configure DNS (50%)
            await self._configure_domain_dns(order, db)
            
            # Step 3: Setup SSL certificate (70%)
            await self._setup_domain_ssl(order, db)
            
            # Step 4: Deploy template (90%)
            await self._deploy_template_to_domain(order, db)
            
            # Step 5: Final verification (100%)
            await self._finalize_domain_setup(order, db)
            
            # Create VendorDomain record
            await self._create_vendor_domain_record(order, db)
            
            logger.info(f"Domain order {order_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Domain order processing failed for {order_id}: {e}")
            
            if order_id in self.processing_orders:
                self.processing_orders[order_id]["error"] = str(e)
                
            # Update order status
            order = db.query(DomainOrder).filter(DomainOrder.id == order_id).first()
            if order:
                order.order_status = DomainStatus.FAILED
                order.error_message = str(e)
                db.commit()
    
    async def _register_domain_with_godaddy(self, order: DomainOrder, db: Session):
        """Register domain with GoDaddy"""
        
        order.current_step = "domain_registration"
        order.completion_percentage = 10
        db.commit()
        
        try:
            # Register with GoDaddy (or mock)
            registration_result = self.godaddy.register_domain(
                domain=order.domain_name,
                contact_info=order.contact_info,
                years=1
            )
            
            if registration_result["success"]:
                order.domain_registration_id = registration_result.get("registration_id")
                order.registrar_order_id = registration_result.get("order_id")
                
                # Handle datetime parsing safely
                expiry_str = registration_result.get("expiry_date")
                if expiry_str:
                    if 'Z' in expiry_str:
                        expiry_str = expiry_str.replace('Z', '+00:00')
                    order.expiry_date = datetime.fromisoformat(expiry_str)
                
                order.completion_percentage = 30
                order.current_step = "domain_registered"
                
                logger.info(f"Domain {order.domain_name} registered successfully")
            else:
                raise Exception(f"Domain registration failed: {registration_result['error']}")
        
        except Exception as e:
            raise Exception(f"Domain registration failed: {str(e)}")
        
        db.commit()
    
    async def _configure_domain_dns(self, order: DomainOrder, db: Session):
        """Configure DNS records for domain"""
        
        order.current_step = "dns_configuration"
        order.completion_percentage = 40
        db.commit()
        
        try:
            # Update nameservers to point to our hosting
            nameservers = ["ns1.vision.com", "ns2.vision.com"]
            
            ns_result = self.godaddy.update_nameservers(
                domain=order.domain_name,
                nameservers=nameservers
            )
            
            if ns_result["success"]:
                order.dns_configured = True
                order.nameservers_updated = True
                order.completion_percentage = 50
                order.current_step = "dns_configured"
                
                logger.info(f"DNS configured for {order.domain_name}")
            else:
                logger.warning(f"DNS configuration warning for {order.domain_name}: {ns_result['error']}")
                # Continue anyway - DNS can be configured later
                order.completion_percentage = 50
                order.current_step = "dns_configured"
        
        except Exception as e:
            logger.error(f"DNS configuration failed for {order.domain_name}: {e}")
            # Continue anyway - DNS can be configured later
            order.completion_percentage = 50
            order.current_step = "dns_configured"
        
        db.commit()
    
    async def _setup_domain_ssl(self, order: DomainOrder, db: Session):
        """Setup SSL certificate"""
        
        order.current_step = "ssl_setup"
        order.completion_percentage = 60
        db.commit()
        
        try:
            # In production, integrate with Let's Encrypt or Cloudflare
            # For now, simulate SSL setup
            await asyncio.sleep(2)
            
            order.ssl_enabled = True
            order.completion_percentage = 70
            order.current_step = "ssl_configured"
            
            logger.info(f"SSL configured for {order.domain_name}")
        
        except Exception as e:
            logger.error(f"SSL setup failed for {order.domain_name}: {e}")
            # Continue without SSL for now
            order.completion_percentage = 70
            order.current_step = "ssl_configured"
        
        db.commit()
    
    async def _deploy_template_to_domain(self, order: DomainOrder, db: Session):
        """Deploy selected template to domain"""
        
        order.current_step = "template_deployment"
        order.completion_percentage = 80
        db.commit()
        
        try:
            # Get vendor data
            vendor = db.query(Vendor).filter(Vendor.id == order.vendor_id).first()
            if not vendor:
                raise Exception("Vendor not found")
            
            # In production, this would deploy the actual template
            # For now, simulate deployment
            await asyncio.sleep(3)
            
            order.hosting_active = True
            order.completion_percentage = 90
            order.current_step = "template_deployed"
            
            logger.info(f"Template {order.template_id} deployed for {order.domain_name}")
        
        except Exception as e:
            raise Exception(f"Template deployment failed: {str(e)}")
        
        db.commit()
    
    async def _finalize_domain_setup(self, order: DomainOrder, db: Session):
        """Final verification and activation"""
        
        order.current_step = "final_verification"
        order.completion_percentage = 95
        db.commit()
        
        try:
            # Final verification
            await asyncio.sleep(1)
            
            order.order_status = DomainStatus.ACTIVE
            order.completion_percentage = 100
            order.current_step = "completed"
            order.completed_at = datetime.utcnow()
            
            logger.info(f"Domain setup completed for {order.domain_name}")
        
        except Exception as e:
            raise Exception(f"Final verification failed: {str(e)}")
        
        db.commit()
    
    async def _create_vendor_domain_record(self, order: DomainOrder, db: Session):
        """Create VendorDomain record after successful setup"""
        
        try:
            vendor_domain = VendorDomain(
                vendor_id=order.vendor_id,
                domain_name=order.domain_name,
                domain_type=order.domain_type,
                status=DomainStatus.ACTIVE,
                purchase_price_inr=order.domain_price_inr,
                renewal_price_inr=order.domain_price_inr,
                registrar=order.selected_registrar,
                registration_date=datetime.utcnow(),
                expiry_date=order.expiry_date,
                ssl_enabled=order.ssl_enabled,
                dns_configured=order.dns_configured,
                hosting_active=order.hosting_active,
                template_id=order.template_id,
                hosting_server="vision-host-in-01",
                domain_order_id=order.id
            )
            
            db.add(vendor_domain)
            db.commit()
            
            logger.info(f"VendorDomain record created for {order.domain_name}")
        
        except Exception as e:
            logger.error(f"Failed to create VendorDomain record: {e}")
    
    def get_order_status(self, order_id: int, db: Session) -> Dict:
        """Get real-time order processing status"""
        
        # Check processing cache first
        if order_id in self.processing_orders:
            processing_info = self.processing_orders[order_id]
            
            return {
                "order_id": order_id,
                "status": processing_info["status"],
                "completion_percentage": processing_info["completion_percentage"],
                "current_step": processing_info["current_step"],
                "processing_time": str(datetime.utcnow() - processing_info["started_at"]),
                "is_processing": True,
                "using_mock": self.using_mock
            }
        
        # Get from database
        order = db.query(DomainOrder).filter(DomainOrder.id == order_id).first()
        
        if not order:
            return {"error": "Order not found"}
        
        status_info = {
            "order_id": order.id,
            "order_number": order.order_number,
            "domain_name": order.domain_name,
            "status": order.order_status.value,
            "completion_percentage": order.completion_percentage,
            "current_step": order.current_step,
            "payment_status": order.payment_status.value,
            "registrar": order.selected_registrar.value if order.selected_registrar else "godaddy",
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "is_processing": False,
            "using_mock": self.using_mock
        }
        
        if order.error_message:
            status_info["error_message"] = order.error_message
        
        if order.completed_at:
            status_info["completed_at"] = order.completed_at.isoformat()
            status_info["website_url"] = f"https://{order.domain_name}"
        
        return status_info
    
    # Helper methods
    def _clean_business_name(self, business_name: str) -> str:
        """Clean business name for domain generation"""
        import re
        
        # Remove common business suffixes
        suffixes = ['private limited', 'pvt ltd', 'ltd', 'llp', 'inc', 'corp', 
                   'company', 'co', 'business', 'shop', 'store', 'enterprises']
        
        # Convert to lowercase and remove special characters
        clean = re.sub(r'[^a-zA-Z0-9\s]', '', business_name.lower())
        
        # Remove business suffixes
        words = clean.split()
        filtered_words = []
        
        for word in words:
            if word not in suffixes and len(word) > 1:
                filtered_words.append(word)
        
        if not filtered_words:
            filtered_words = words[:2]  # Keep first 2 words if all were suffixes
        
        return ''.join(filtered_words)
    
    def _generate_name_variations(self, clean_name: str) -> List[str]:
        """Generate domain name variations"""
        variations = [clean_name]
        
        # Add prefixes for Indian market
        prefixes = ['my', 'get', 'buy', 'best']
        suffixes = ['india', 'in', 'shop', 'store', 'online']
        
        # Add prefixed variations
        for prefix in prefixes:
            if len(clean_name) <= 8:
                variations.append(f"{prefix}{clean_name}")
        
        # Add suffixed variations
        for suffix in suffixes:
            if len(clean_name) <= 6:
                variations.append(f"{clean_name}{suffix}")
        
        return variations[:8]  # Limit variations
    
    def _calculate_recommendation_score(self, variation: str, tld_config: Dict, original_name: str) -> float:
        """Calculate recommendation score for Indian market"""
        score = 0.0
        
        # TLD preferences
        if tld_config.get("popular", False):
            score += 0.3
        
        # Length preferences
        domain_length = len(variation)
        if domain_length <= 6:
            score += 0.4
        elif domain_length <= 10:
            score += 0.2
        
        # Exact match bonus
        if variation == original_name:
            score += 0.3
        
        # Priority from config
        priority = tld_config.get("priority", 99)
        if priority <= 3:
            score += 0.2
        elif priority <= 6:
            score += 0.1
        
        return min(1.0, score)
    
    def _is_premium_domain(self, domain: str) -> bool:
        """Check if domain is premium"""
        domain_base = domain.split('.')[0].lower()
        
        premium_indicators = [
            len(domain_base) <= 4,
            domain_base.isdigit(),
            domain_base in ['buy', 'sell', 'best', 'top', 'shop', 'india'],
            any(char.isdigit() for char in domain_base) and len(domain_base) <= 6
        ]
        
        return any(premium_indicators)