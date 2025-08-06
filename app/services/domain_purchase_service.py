# app/services/domain_purchase_service.py
"""
Step 2: Domain Purchase & Payment Processing Service
Integrates with existing Vision platform architecture

Features:
- Domain purchase order management
- Payment processing with multiple gateways
- Template selection integration
- Order tracking and status updates
- Background processing for domain registration
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import json
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.domain import VendorDomain, DomainStatus, DomainType
from app.models.vendor import Vendor
from app.services.multi_registrar_service import multi_registrar_service
from app.core.monitoring import monitoring

logger = logging.getLogger(__name__)

class OrderStatus(str, Enum):
    PENDING = "pending"           # Order created, awaiting payment
    PAYMENT_PROCESSING = "payment_processing"  # Payment being processed
    PAYMENT_FAILED = "payment_failed"          # Payment failed
    PAID = "paid"                # Payment successful
    PROCESSING = "processing"     # Domain registration in progress
    COMPLETED = "completed"       # Domain registered and live
    FAILED = "failed"            # Domain registration failed
    CANCELLED = "cancelled"       # Order cancelled

class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    BANK_TRANSFER = "bank_transfer"
    CRYPTO = "crypto"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

@dataclass
class ContactInfo:
    """Customer contact information for domain registration"""
    first_name: str
    last_name: str
    email: str
    phone: str
    company: Optional[str] = None
    address_line1: str = ""
    address_line2: Optional[str] = None
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"
    
    def validate(self) -> List[str]:
        """Validate contact information and return list of errors"""
        errors = []
        
        if not self.first_name or len(self.first_name.strip()) < 2:
            errors.append("First name must be at least 2 characters")
        
        if not self.last_name or len(self.last_name.strip()) < 2:
            errors.append("Last name must be at least 2 characters")
        
        if not self.email or '@' not in self.email:
            errors.append("Valid email address is required")
        
        if not self.phone or len(self.phone.strip()) < 10:
            errors.append("Valid phone number is required")
        
        if not self.address_line1 or len(self.address_line1.strip()) < 5:
            errors.append("Valid address is required")
        
        if not self.city or len(self.city.strip()) < 2:
            errors.append("City is required")
        
        if not self.postal_code or len(self.postal_code.strip()) < 3:
            errors.append("Valid postal code is required")
        
        return errors

@dataclass
class PaymentInfo:
    """Payment information for processing"""
    payment_method: PaymentMethod
    amount: float
    currency: str
    
    # Credit card info (if applicable)
    card_number: Optional[str] = None
    card_expiry: Optional[str] = None
    card_cvv: Optional[str] = None
    cardholder_name: Optional[str] = None
    
    # PayPal info
    paypal_email: Optional[str] = None
    
    # Bank transfer info
    bank_account: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate payment information"""
        errors = []
        
        if self.amount <= 0:
            errors.append("Payment amount must be greater than 0")
        
        if self.payment_method == PaymentMethod.CREDIT_CARD:
            if not self.card_number or len(self.card_number.replace(' ', '')) < 13:
                errors.append("Valid credit card number is required")
            
            if not self.card_expiry or len(self.card_expiry) != 5:  # MM/YY format
                errors.append("Valid expiry date is required (MM/YY)")
            
            if not self.card_cvv or len(self.card_cvv) < 3:
                errors.append("Valid CVV is required")
            
            if not self.cardholder_name or len(self.cardholder_name.strip()) < 2:
                errors.append("Cardholder name is required")
        
        elif self.payment_method == PaymentMethod.PAYPAL:
            if not self.paypal_email or '@' not in self.paypal_email:
                errors.append("Valid PayPal email is required")
        
        return errors

@dataclass
class DomainOrder:
    """Complete domain purchase order"""
    id: str
    vendor_id: int
    domain: str
    
    # Pricing information
    wholesale_price: float
    customer_price: float
    currency: str
    margin_amount: float
    registrar: str
    
    # Order details
    contact_info: ContactInfo
    payment_info: PaymentInfo
    template_id: int
    registration_years: int = 1
    
    # Status tracking
    status: OrderStatus = OrderStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = None
    updated_at: datetime = None
    
    # Processing details
    payment_id: Optional[str] = None
    domain_registration_id: Optional[str] = None
    error_message: Optional[str] = None
    completion_percentage: int = 0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

class DomainPurchaseService:
    """
    Service for handling domain purchases with payment processing
    """
    
    def __init__(self):
        # In-memory order storage for demo (in production, use database)
        self.orders: Dict[str, DomainOrder] = {}
        
        # Payment gateway configurations
        self.payment_gateways = {
            PaymentMethod.STRIPE: {
                "api_key": "sk_test_...",  # Your Stripe secret key
                "public_key": "pk_test_...",  # Your Stripe public key
                "webhook_secret": "whsec_...",
                "enabled": True
            },
            PaymentMethod.PAYPAL: {
                "client_id": "your_paypal_client_id",
                "client_secret": "your_paypal_secret",
                "sandbox": True,  # Set to False for production
                "enabled": True
            }
        }
    
    async def create_purchase_order(
        self,
        vendor_id: int,
        domain: str,
        contact_info: Dict[str, str],
        payment_method: str,
        template_id: int,
        customer_location: str = "US"
    ) -> Dict[str, Any]:
        """
        Create a new domain purchase order
        """
        try:
            # Validate inputs
            if not domain or '.' not in domain:
                raise ValueError("Invalid domain name")
            
            # Get current pricing for the domain
            pricing_result = await multi_registrar_service.get_domain_pricing(
                domain, customer_location
            )
            
            if not pricing_result.available:
                raise ValueError(f"Domain {domain} is not available for registration")
            
            # Create contact info object
            contact = ContactInfo(
                first_name=contact_info.get('first_name', ''),
                last_name=contact_info.get('last_name', ''),
                email=contact_info.get('email', ''),
                phone=contact_info.get('phone', ''),
                company=contact_info.get('company'),
                address_line1=contact_info.get('address_line1', ''),
                address_line2=contact_info.get('address_line2'),
                city=contact_info.get('city', ''),
                state=contact_info.get('state', ''),
                postal_code=contact_info.get('postal_code', ''),
                country=contact_info.get('country', 'US')
            )
            
            # Validate contact information
            contact_errors = contact.validate()
            if contact_errors:
                raise ValueError(f"Contact validation failed: {', '.join(contact_errors)}")
            
            # Create payment info object
            payment = PaymentInfo(
                payment_method=PaymentMethod(payment_method),
                amount=pricing_result.customer_price,
                currency=pricing_result.customer_currency
            )
            
            # Generate unique order ID
            order_id = f"DOM_{uuid.uuid4().hex[:8].upper()}"
            
            # Create order
            order = DomainOrder(
                id=order_id,
                vendor_id=vendor_id,
                domain=domain,
                wholesale_price=pricing_result.wholesale_price,
                customer_price=pricing_result.customer_price,
                currency=pricing_result.customer_currency,
                margin_amount=pricing_result.margin_amount,
                registrar=pricing_result.wholesale_registrar,
                contact_info=contact,
                payment_info=payment,
                template_id=template_id
            )
            
            # Store order
            self.orders[order_id] = order
            
            # Log order creation
            monitoring.record_request(success=True, response_time_ms=0)
            logger.info(f"Domain purchase order created: {order_id} for {domain}")
            
            return {
                "success": True,
                "order_id": order_id,
                "domain": domain,
                "amount": pricing_result.customer_price,
                "currency": pricing_result.customer_currency,
                "status": order.status.value,
                "payment_methods": self._get_available_payment_methods(),
                "next_step": "process_payment"
            }
            
        except Exception as e:
            logger.error(f"Failed to create purchase order: {e}")
            monitoring.record_error(str(e))
            raise
    
    async def process_payment(
        self,
        order_id: str,
        payment_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process payment for a domain order
        """
        try:
            order = self.orders.get(order_id)
            if not order:
                raise ValueError(f"Order {order_id} not found")
            
            if order.status != OrderStatus.PENDING:
                raise ValueError(f"Order {order_id} is not in pending status")
            
            # Update order status
            order.status = OrderStatus.PAYMENT_PROCESSING
            order.payment_status = PaymentStatus.PROCESSING
            order.updated_at = datetime.utcnow()
            
            # Process payment based on method
            payment_result = await self._process_payment_gateway(order, payment_details)
            
            if payment_result["success"]:
                # Payment successful
                order.status = OrderStatus.PAID
                order.payment_status = PaymentStatus.COMPLETED
                order.payment_id = payment_result["payment_id"]
                order.completion_percentage = 25  # Payment completed
                
                # Start domain registration process (async)
                asyncio.create_task(self._process_domain_registration(order_id))
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "payment_id": payment_result["payment_id"],
                    "status": order.status.value,
                    "message": "Payment processed successfully. Domain registration starting.",
                    "estimated_completion": "5-10 minutes"
                }
            else:
                # Payment failed
                order.status = OrderStatus.PAYMENT_FAILED
                order.payment_status = PaymentStatus.FAILED
                order.error_message = payment_result["error"]
                
                return {
                    "success": False,
                    "order_id": order_id,
                    "error": payment_result["error"],
                    "status": order.status.value
                }
                
        except Exception as e:
            logger.error(f"Payment processing failed for order {order_id}: {e}")
            
            # Update order status on error
            if order_id in self.orders:
                self.orders[order_id].status = OrderStatus.PAYMENT_FAILED
                self.orders[order_id].error_message = str(e)
            
            return {
                "success": False,
                "order_id": order_id,
                "error": str(e),
                "status": "payment_failed"
            }
    
    async def _process_payment_gateway(
        self,
        order: DomainOrder,
        payment_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process payment through appropriate gateway
        """
        try:
            payment_method = order.payment_info.payment_method
            
            if payment_method == PaymentMethod.STRIPE:
                return await self._process_stripe_payment(order, payment_details)
            elif payment_method == PaymentMethod.PAYPAL:
                return await self._process_paypal_payment(order, payment_details)
            else:
                # For demo purposes, simulate successful payment
                await asyncio.sleep(2)  # Simulate processing time
                
                return {
                    "success": True,
                    "payment_id": f"pay_{uuid.uuid4().hex[:12]}",
                    "transaction_id": f"txn_{uuid.uuid4().hex[:16]}",
                    "gateway": payment_method.value
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _process_stripe_payment(
        self,
        order: DomainOrder,
        payment_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process payment through Stripe
        """
        try:
            # In production, you would use the actual Stripe API
            # import stripe
            # stripe.api_key = self.payment_gateways[PaymentMethod.STRIPE]["api_key"]
            
            # For demo, simulate Stripe payment
            await asyncio.sleep(3)  # Simulate API call
            
            # Simulate 95% success rate
            import random
            if random.random() < 0.95:
                return {
                    "success": True,
                    "payment_id": f"pi_{uuid.uuid4().hex[:16]}",
                    "transaction_id": f"ch_{uuid.uuid4().hex[:16]}",
                    "gateway": "stripe"
                }
            else:
                return {
                    "success": False,
                    "error": "Your card was declined. Please try a different payment method."
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Stripe payment failed: {str(e)}"
            }
    
    async def _process_paypal_payment(
        self,
        order: DomainOrder,
        payment_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process payment through PayPal
        """
        try:
            # In production, you would use the PayPal SDK
            # For demo, simulate PayPal payment
            await asyncio.sleep(4)  # Simulate redirect and confirmation
            
            return {
                "success": True,
                "payment_id": f"PAYID-{uuid.uuid4().hex[:16].upper()}",
                "transaction_id": f"TXN-{uuid.uuid4().hex[:12].upper()}",
                "gateway": "paypal"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"PayPal payment failed: {str(e)}"
            }
    
    async def _process_domain_registration(self, order_id: str):
        """
        Background task to register the domain and setup hosting
        """
        try:
            order = self.orders.get(order_id)
            if not order:
                logger.error(f"Order {order_id} not found for domain registration")
                return
            
            # Update status
            order.status = OrderStatus.PROCESSING
            order.completion_percentage = 30
            order.updated_at = datetime.utcnow()
            
            # Step 1: Register domain with registrar
            logger.info(f"Starting domain registration for {order.domain}")
            await self._register_domain_with_registrar(order)
            order.completion_percentage = 60
            
            # Step 2: Setup DNS
            logger.info(f"Configuring DNS for {order.domain}")
            await self._configure_domain_dns(order)
            order.completion_percentage = 80
            
            # Step 3: Deploy template (integrate with existing template system)
            logger.info(f"Deploying template {order.template_id} for {order.domain}")
            await self._deploy_template_to_domain(order)
            order.completion_percentage = 90
            
            # Step 4: Verify everything is working
            logger.info(f"Verifying domain setup for {order.domain}")
            await self._verify_domain_setup(order)
            
            # Mark as completed
            order.status = OrderStatus.COMPLETED
            order.completion_percentage = 100
            order.updated_at = datetime.utcnow()
            
            logger.info(f"Domain registration completed for {order.domain}")
            
        except Exception as e:
            logger.error(f"Domain registration failed for order {order_id}: {e}")
            
            if order_id in self.orders:
                self.orders[order_id].status = OrderStatus.FAILED
                self.orders[order_id].error_message = str(e)
                self.orders[order_id].updated_at = datetime.utcnow()
    
    async def _register_domain_with_registrar(self, order: DomainOrder):
        """Register domain with the cheapest registrar"""
        # Simulate domain registration API call
        await asyncio.sleep(5)
        
        # In production, call actual registrar API
        order.domain_registration_id = f"REG_{uuid.uuid4().hex[:12].upper()}"
    
    async def _configure_domain_dns(self, order: DomainOrder):
        """Configure DNS for the domain"""
        # Simulate DNS configuration
        await asyncio.sleep(3)
        
        # In production, configure actual DNS records
        pass
    
    async def _deploy_template_to_domain(self, order: DomainOrder):
        """Deploy the selected template to the domain"""
        # Simulate template deployment
        await asyncio.sleep(4)
        
        # In production, integrate with your existing template system
        # This would connect to your VendorStorePage template selection
        pass
    
    async def _verify_domain_setup(self, order: DomainOrder):
        """Verify that the domain is properly configured and accessible"""
        # Simulate verification
        await asyncio.sleep(2)
        
        # In production, make HTTP requests to verify the site is live
        pass
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get current status of a domain order"""
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        # Calculate estimated time remaining
        time_remaining = self._estimate_time_remaining(order)
        
        return {
            "order_id": order_id,
            "domain": order.domain,
            "status": order.status.value,
            "payment_status": order.payment_status.value,
            "completion_percentage": order.completion_percentage,
            "estimated_time_remaining": time_remaining,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "error_message": order.error_message,
            "payment_id": order.payment_id,
            "domain_registration_id": order.domain_registration_id,
            "template_id": order.template_id,
            "steps": self._get_order_steps(order)
        }
    
    def _estimate_time_remaining(self, order: DomainOrder) -> str:
        """Estimate time remaining for order completion"""
        if order.status == OrderStatus.COMPLETED:
            return "Completed"
        elif order.status == OrderStatus.FAILED:
            return "Failed"
        elif order.completion_percentage < 30:
            return "8-12 minutes"
        elif order.completion_percentage < 60:
            return "5-8 minutes"
        elif order.completion_percentage < 90:
            return "2-5 minutes"
        else:
            return "1-2 minutes"
    
    def _get_order_steps(self, order: DomainOrder) -> List[Dict[str, Any]]:
        """Get detailed steps for order progress"""
        steps = [
            {
                "step": "Payment Processing",
                "status": "completed" if order.payment_status == PaymentStatus.COMPLETED else "pending",
                "description": "Process payment for domain registration"
            },
            {
                "step": "Domain Registration",
                "status": "completed" if order.completion_percentage >= 60 else "pending",
                "description": f"Register {order.domain} with {order.registrar}"
            },
            {
                "step": "DNS Configuration",
                "status": "completed" if order.completion_percentage >= 80 else "pending",
                "description": "Configure DNS settings for your domain"
            },
            {
                "step": "Template Deployment",
                "status": "completed" if order.completion_percentage >= 90 else "pending",
                "description": f"Deploy Template {order.template_id} to your domain"
            },
            {
                "step": "Final Verification",
                "status": "completed" if order.status == OrderStatus.COMPLETED else "pending",
                "description": "Verify your website is live and accessible"
            }
        ]
        return steps
    
    def _get_available_payment_methods(self) -> List[Dict[str, Any]]:
        """Get list of available payment methods"""
        methods = []
        
        for method, config in self.payment_gateways.items():
            if config.get("enabled", False):
                methods.append({
                    "id": method.value,
                    "name": method.value.replace("_", " ").title(),
                    "icon": self._get_payment_method_icon(method),
                    "description": self._get_payment_method_description(method)
                })
        
        # Always include credit card as fallback
        if not any(m["id"] == "credit_card" for m in methods):
            methods.append({
                "id": "credit_card",
                "name": "Credit Card",
                "icon": "💳",
                "description": "Visa, Mastercard, American Express"
            })
        
        return methods
    
    def _get_payment_method_icon(self, method: PaymentMethod) -> str:
        """Get emoji icon for payment method"""
        icons = {
            PaymentMethod.CREDIT_CARD: "💳",
            PaymentMethod.PAYPAL: "🅿️",
            PaymentMethod.STRIPE: "💳",
            PaymentMethod.BANK_TRANSFER: "🏦",
            PaymentMethod.CRYPTO: "₿"
        }
        return icons.get(method, "💰")
    
    def _get_payment_method_description(self, method: PaymentMethod) -> str:
        """Get description for payment method"""
        descriptions = {
            PaymentMethod.CREDIT_CARD: "Visa, Mastercard, American Express",
            PaymentMethod.PAYPAL: "Pay securely with your PayPal account",
            PaymentMethod.STRIPE: "Secure card processing by Stripe",
            PaymentMethod.BANK_TRANSFER: "Direct bank transfer",
            PaymentMethod.CRYPTO: "Bitcoin and other cryptocurrencies"
        }
        return descriptions.get(method, "Secure payment processing")
    
    def list_orders(self, vendor_id: int) -> List[Dict[str, Any]]:
        """List all orders for a vendor"""
        vendor_orders = [
            order for order in self.orders.values() 
            if order.vendor_id == vendor_id
        ]
        
        # Sort by creation date (newest first)
        vendor_orders.sort(key=lambda x: x.created_at, reverse=True)
        
        return [
            {
                "order_id": order.id,
                "domain": order.domain,
                "status": order.status.value,
                "amount": order.customer_price,
                "currency": order.currency,
                "created_at": order.created_at.isoformat(),
                "completion_percentage": order.completion_percentage
            }
            for order in vendor_orders
        ]

# Global service instance
domain_purchase_service = DomainPurchaseService()