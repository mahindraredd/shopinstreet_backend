# app/services/domain_config.py - FIXED VERSION
from typing import Dict, List, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class DomainConfig:
    """Production domain service configuration for Indian market"""
    
    # Indian TLD Configuration with INR pricing (GoDaddy-based)
    INDIAN_TLD_CONFIG = {
        "com": {
            "price_inr": 999,
            "renewal_inr": 1199,
            "popular": True,
            "godaddy_supported": True,
            "priority": 1
        },
        "in": {
            "price_inr": 699,
            "renewal_inr": 899,
            "popular": True,
            "godaddy_supported": True,
            "priority": 2
        },
        "co.in": {
            "price_inr": 599,
            "renewal_inr": 799,
            "popular": True,
            "godaddy_supported": True,
            "priority": 3
        },
        "net.in": {
            "price_inr": 599,
            "renewal_inr": 799,
            "popular": False,
            "godaddy_supported": True,
            "priority": 4
        },
        "org.in": {
            "price_inr": 599,
            "renewal_inr": 799,
            "popular": False,
            "godaddy_supported": True,
            "priority": 5
        },
        "shop": {
            "price_inr": 2999,
            "renewal_inr": 3299,
            "popular": True,
            "godaddy_supported": True,
            "priority": 6
        },
        "store": {
            "price_inr": 4999,
            "renewal_inr": 4999,
            "popular": False,
            "godaddy_supported": True,
            "priority": 7
        },
        "co": {
            "price_inr": 2499,
            "renewal_inr": 2499,
            "popular": True,
            "godaddy_supported": True,
            "priority": 8
        },
        "online": {
            "price_inr": 3499,
            "renewal_inr": 3499,
            "popular": False,
            "godaddy_supported": True,
            "priority": 9
        },
        "site": {
            "price_inr": 2999,
            "renewal_inr": 2999,
            "popular": False,
            "godaddy_supported": True,
            "priority": 10
        }
    }
    
    # GoDaddy Configuration
    GODADDY_CONFIG = {
        "name": "GoDaddy",
        "test_endpoint": "https://api.ote-godaddy.com",
        "prod_endpoint": "https://api.godaddy.com",
        "supported_features": [
            "domain_registration", 
            "dns_management", 
            "domain_transfer",
            "domain_availability"
        ],
        "indian_tld_support": True,
        "commission_percentage": 0.0  # No commission, direct pricing
    }
    
    @classmethod
    def get_tld_pricing(cls, tld: str) -> Dict:
        """Get pricing for a specific TLD"""
        return cls.INDIAN_TLD_CONFIG.get(tld, {
            "price_inr": 999,
            "renewal_inr": 1199,
            "popular": False,
            "godaddy_supported": True,
            "priority": 99
        })
    
    @classmethod
    def get_supported_tlds(cls) -> List[str]:
        """Get list of supported TLDs ordered by priority"""
        return sorted(
            cls.INDIAN_TLD_CONFIG.keys(),
            key=lambda tld: cls.INDIAN_TLD_CONFIG[tld]["priority"]
        )
    
    @classmethod
    def get_tlds_by_priority(cls) -> List[str]:
        """✅ MISSING METHOD - Get TLDs ordered by priority (lowest priority number first)"""
        return sorted(
            cls.INDIAN_TLD_CONFIG.keys(),
            key=lambda tld: cls.INDIAN_TLD_CONFIG[tld]["priority"]
        )
    
    @classmethod
    def get_popular_tlds(cls) -> List[str]:
        """Get list of popular TLDs for prioritization"""
        return [tld for tld, config in cls.INDIAN_TLD_CONFIG.items() if config["popular"]]
    
    @classmethod
    def get_cheapest_tlds(cls) -> List[str]:
        """Get TLDs ordered by price (cheapest first)"""
        return sorted(
            cls.INDIAN_TLD_CONFIG.keys(),
            key=lambda tld: cls.INDIAN_TLD_CONFIG[tld]["price_inr"]
        )
    
    @classmethod
    def get_tld_info(cls, tld: str) -> Optional[Dict]:
        """Get complete information for a specific TLD"""
        return cls.INDIAN_TLD_CONFIG.get(tld)
    
    @classmethod
    def is_indian_tld(cls, tld: str) -> bool:
        """Check if TLD is an Indian domain"""
        indian_tlds = {"in", "co.in", "net.in", "org.in", "firm.in", "gen.in", "ind.in"}
        return tld.lower() in indian_tlds
    
    @classmethod
    def validate_config(cls) -> Dict[str, bool]:
        """Validate domain service configuration"""
        validation_results = {
            "godaddy_configured": bool(settings.GODADDY_API_KEY and settings.GODADDY_API_SECRET),
            "domain_settings_configured": bool(
                getattr(settings, 'DOMAIN_HOSTING_IP', None) and 
                getattr(settings, 'DOMAIN_SETUP_EMAIL', None)
            ),
            "environment_set": bool(getattr(settings, 'GODADDY_ENVIRONMENT', None))
        }
        
        # Log configuration status
        for config_name, status in validation_results.items():
            if status:
                logger.info(f"✅ {config_name}: Configured")
            else:
                logger.warning(f"⚠️  {config_name}: Not configured")
        
        return validation_results
    
    @classmethod
    def get_environment_info(cls) -> Dict:
        """Get current environment configuration"""
        godaddy_env = getattr(settings, 'GODADDY_ENVIRONMENT', 'NOT_SET')
        
        return {
            "godaddy_environment": godaddy_env,
            "is_production": godaddy_env == "PRODUCTION",
            "is_test": godaddy_env == "OTE",
            "api_endpoint": (
                cls.GODADDY_CONFIG["prod_endpoint"] 
                if godaddy_env == "PRODUCTION" 
                else cls.GODADDY_CONFIG["test_endpoint"]
            ),
            "supported_tlds": len(cls.INDIAN_TLD_CONFIG),
            "total_config_items": len(cls.INDIAN_TLD_CONFIG)
        }
    
    @classmethod
    def get_price_range(cls) -> Dict[str, float]:
        """Get price range for all TLDs"""
        prices = [config["price_inr"] for config in cls.INDIAN_TLD_CONFIG.values()]
        return {
            "min_price": min(prices),
            "max_price": max(prices),
            "average_price": sum(prices) / len(prices)
        }
    
    @classmethod
    def filter_tlds_by_price(cls, max_price_inr: float) -> List[str]:
        """Get TLDs under a specific price point"""
        return [
            tld for tld, config in cls.INDIAN_TLD_CONFIG.items()
            if config["price_inr"] <= max_price_inr
        ]
    
    @classmethod
    def get_recommendations_for_business_type(cls, business_type: str) -> List[str]:
        """Get TLD recommendations based on business type"""
        recommendations = {
            "ecommerce": ["com", "shop", "store", "co.in"],
            "restaurant": ["com", "in", "co.in", "food"],
            "services": ["com", "in", "co.in", "service"],
            "tech": ["com", "in", "co", "tech"],
            "education": ["org.in", "com", "in"],
            "nonprofit": ["org.in", "org", "com"],
            "personal": ["in", "com", "co.in"],
            "blog": ["com", "in", "online"],
            "portfolio": ["com", "in", "co.in", "site"]
        }
        
        # Get recommendations for business type, fallback to general recommendations
        tld_list = recommendations.get(business_type.lower(), ["com", "in", "co.in"])
        
        # Filter to only include TLDs we support
        return [tld for tld in tld_list if tld in cls.INDIAN_TLD_CONFIG]