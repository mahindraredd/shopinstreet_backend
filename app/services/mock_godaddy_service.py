# app/services/mock_godaddy_service.py
import logging
from typing import Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MockGoDaddyService:
    """Mock GoDaddy service for testing when API is unavailable"""
    
    def __init__(self):
        self.api_key = "mock_key"
        self.api_secret = "mock_secret"
        self.environment = "MOCK"
        self.base_url = "https://mock-api.godaddy.com"
        
        logger.info("Mock GoDaddy service initialized")
    
    def check_domain_availability(self, domain: str) -> Dict:
        """Mock domain availability check"""
        
        # Simulate different availability scenarios
        unavailable_domains = [
            "google.com", "microsoft.com", "amazon.com", 
            "test.com", "example.com", "facebook.com"
        ]
        
        is_available = domain.lower() not in unavailable_domains
        
        # Mock pricing based on TLD
        tld = domain.split('.')[-1]
        mock_prices = {
            'com': 12.0, 'in': 8.5, 'co.in': 7.2,
            'shop': 36.0, 'store': 60.0, 'co': 30.0
        }
        
        base_price = mock_prices.get(tld, 12.0)
        inr_price = base_price * 83
        
        return {
            "available": is_available,
            "domain": domain,
            "price": inr_price,
            "currency": "INR",
            "period": 1,
            "definitive": True,
            "checked_at": datetime.utcnow().isoformat(),
            "mock": True
        }
    
    def register_domain(self, domain: str, contact_info: Dict, years: int = 1) -> Dict:
        """Mock domain registration"""
        
        # Always succeed for testing
        return {
            "success": True,
            "domain": domain,
            "order_id": f"MOCK_{domain.replace('.', '_').upper()}",
            "status": "registered",
            "expiry_date": (datetime.utcnow() + timedelta(days=365*years)).isoformat(),
            "nameservers": ["ns1.vision.com", "ns2.vision.com"],
            "registration_id": f"REG_MOCK_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "mock": True
        }
    
    def get_domain_details(self, domain: str) -> Dict:
        """Mock domain details"""
        return {
            "success": True,
            "domain": domain,
            "status": "ACTIVE",
            "created_at": datetime.utcnow().isoformat(),
            "expires": (datetime.utcnow() + timedelta(days=365)).isoformat(),
            "nameservers": ["ns1.vision.com", "ns2.vision.com"],
            "locked": False,
            "privacy": False,
            "mock": True
        }
    
    def update_nameservers(self, domain: str, nameservers: List[str]) -> Dict:
        """Mock nameserver update"""
        return {
            "success": True,
            "domain": domain,
            "nameservers": nameservers,
            "message": "Nameservers updated successfully (mock)",
            "mock": True
        }
    
    def test_connection(self) -> Dict:
        """Mock connection test"""
        return {
            "success": True,
            "environment": "MOCK",
            "endpoint": self.base_url,
            "message": "Mock GoDaddy API connection successful",
            "mock": True
        }