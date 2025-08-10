# app/services/real_pricing_service.py
"""
Real-time domain pricing from GoDaddy API
Replaces static pricing with dynamic, accurate pricing
"""

import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from app.services.godaddy_service import GoDaddyService
from app.services.domain_config import DomainConfig

logger = logging.getLogger(__name__)

class RealPricingService:
    """Get real-time domain pricing from GoDaddy API"""
    
    def __init__(self):
        self.godaddy = GoDaddyService()
        
        # Pricing configuration
        self.exchange_rate = 83.0  # USD to INR (update this regularly)
        self.markup_percentage = 0.15  # 15% markup on GoDaddy wholesale price
        self.min_prices = {  # Minimum prices to ensure profitability
            "com": 950,
            "in": 650, 
            "co.in": 550,
            "shop": 2800,
            "store": 4500
        }
        
        logger.info("Real pricing service initialized with 15% markup")
    
    def get_real_domain_price(self, domain: str) -> Dict:
        """Get real-time price from GoDaddy API for single domain"""
        
        try:
            logger.info(f"🔍 Getting real price for: {domain}")
            
            # Call GoDaddy API for availability + pricing
            result = self.godaddy.check_domain_availability(domain)
            
            if not result.get("success", True):
                return self._fallback_to_static_price(domain, f"API error: {result.get('error')}")
            
            if not result.get("available", False):
                return {
                    "success": False,
                    "domain": domain,
                    "available": False,
                    "error": "Domain not available for registration"
                }
            
            # Extract USD price from GoDaddy response
            usd_price = result.get("price", 0)
            
            # Handle cases where GoDaddy doesn't return price
            if usd_price == 0:
                logger.warning(f"⚠️ No price returned from GoDaddy for {domain}")
                return self._fallback_to_static_price(domain, "No price in API response")
            
            # Convert USD to INR with markup
            base_inr_price = usd_price * self.exchange_rate
            markup_amount = base_inr_price * self.markup_percentage
            final_price = base_inr_price + markup_amount
            
            # Apply minimum price protection
            tld = domain.split('.')[-1]
            min_price = self.min_prices.get(tld, 0)
            if final_price < min_price:
                logger.info(f"💰 Applying minimum price for {domain}: ₹{min_price}")
                final_price = min_price
                markup_percentage = ((final_price - base_inr_price) / base_inr_price) * 100
            else:
                markup_percentage = self.markup_percentage * 100
            
            logger.info(f"✅ Real price for {domain}: ${usd_price} USD → ₹{final_price:.0f} INR")
            
            return {
                "success": True,
                "domain": domain,
                "available": True,
                "price_usd": usd_price,
                "price_inr_base": round(base_inr_price, 2),
                "price_inr": round(final_price, 2),
                "price_display": f"₹{final_price:,.0f}",
                "exchange_rate": self.exchange_rate,
                "markup_percentage": round(markup_percentage, 1),
                "markup_amount": round(markup_amount, 2),
                "source": "godaddy_api",
                "checked_at": datetime.now().isoformat(),
                "profit_margin": round(markup_amount, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Real pricing failed for {domain}: {e}")
            return self._fallback_to_static_price(domain, str(e))
    
    def _fallback_to_static_price(self, domain: str, reason: str) -> Dict:
        """Fallback to static pricing when API fails"""
        
        tld = domain.split('.')[-1]
        static_config = DomainConfig.get_tld_pricing(tld)
        
        logger.warning(f"⚠️ Using static pricing for {domain}: {reason}")
        
        return {
            "success": True,
            "domain": domain,
            "available": True,  # Assume available for static pricing
            "price_inr": static_config["price_inr"],
            "price_display": f"₹{static_config['price_inr']:,}",
            "source": "static_fallback",
            "fallback_reason": reason,
            "checked_at": datetime.now().isoformat(),
            "note": "Price may not be current - API unavailable"
        }
    
    async def get_bulk_real_prices(self, domains: List[str]) -> Dict[str, Dict]:
        """Get real prices for multiple domains efficiently"""
        
        logger.info(f"🔍 Getting real prices for {len(domains)} domains...")
        
        results = {}
        success_count = 0
        fallback_count = 0
        
        for i, domain in enumerate(domains):
            logger.info(f"Checking {i+1}/{len(domains)}: {domain}")
            
            price_info = self.get_real_domain_price(domain)
            results[domain] = price_info
            
            # Track success rate
            if price_info.get("source") == "godaddy_api":
                success_count += 1
            else:
                fallback_count += 1
            
            # Rate limiting - don't hammer GoDaddy API
            if i < len(domains) - 1:  # Don't sleep after last domain
                await asyncio.sleep(0.2)  # 200ms between requests
        
        logger.info(f"✅ Bulk pricing complete: {success_count} real prices, {fallback_count} fallbacks")
        
        return results
    
    def update_domain_suggestions_with_real_prices(self, suggestions: List[Dict]) -> List[Dict]:
        """Replace static prices in suggestions with real GoDaddy prices"""
        
        logger.info(f"🔄 Updating {len(suggestions)} suggestions with real prices...")
        
        updated_suggestions = []
        
        for suggestion in suggestions:
            domain_name = suggestion["suggested_domain"]
            
            # Get real price for this domain
            real_price_info = self.get_real_domain_price(domain_name)
            
            if real_price_info.get("success"):
                # Update suggestion with real pricing data
                suggestion.update({
                    # Replace static prices with real prices
                    "registration_price_inr": real_price_info["price_inr"],
                    "registration_price_display": real_price_info["price_display"],
                    
                    # Add real pricing metadata
                    "real_pricing": {
                        "godaddy_price_usd": real_price_info.get("price_usd", 0),
                        "base_price_inr": real_price_info.get("price_inr_base", 0),
                        "markup_percentage": real_price_info.get("markup_percentage", 0),
                        "profit_margin_inr": real_price_info.get("profit_margin", 0),
                        "source": real_price_info.get("source", "unknown"),
                        "exchange_rate": real_price_info.get("exchange_rate", 83)
                    },
                    
                    # Update availability (real check)
                    "is_available": real_price_info.get("available", True),
                    
                    # Pricing source indicator
                    "pricing_updated": True,
                    "last_price_check": real_price_info.get("checked_at")
                })
                
                # Log price update
                source = real_price_info.get("source", "unknown")
                price = real_price_info["price_inr"]
                logger.info(f"✅ {domain_name}: ₹{price:.0f} ({source})")
                
            else:
                # Keep original static pricing if real pricing fails
                logger.warning(f"⚠️ {domain_name}: Keeping static price (real pricing failed)")
                suggestion["pricing_updated"] = False
                suggestion["pricing_error"] = real_price_info.get("error", "Unknown error")
            
            updated_suggestions.append(suggestion)
        
        # Calculate new cheapest price
        available_prices = [
            s["registration_price_inr"] for s in updated_suggestions 
            if s.get("is_available", True)
        ]
        cheapest_price = min(available_prices) if available_prices else 0
        
        logger.info(f"💰 Cheapest real price: ₹{cheapest_price}")
        
        return updated_suggestions, cheapest_price
    
    def get_pricing_summary(self, suggestions: List[Dict]) -> Dict:
        """Get summary of pricing sources and accuracy"""
        
        total_domains = len(suggestions)
        real_api_count = sum(1 for s in suggestions if s.get("real_pricing", {}).get("source") == "godaddy_api")
        static_count = total_domains - real_api_count
        
        # Calculate average markup
        real_markups = [
            s.get("real_pricing", {}).get("markup_percentage", 0) 
            for s in suggestions 
            if s.get("real_pricing", {}).get("source") == "godaddy_api"
        ]
        avg_markup = sum(real_markups) / len(real_markups) if real_markups else 0
        
        return {
            "total_domains": total_domains,
            "real_api_prices": real_api_count,
            "static_fallback_prices": static_count,
            "accuracy_percentage": round((real_api_count / total_domains) * 100, 1),
            "average_markup_percentage": round(avg_markup, 1),
            "exchange_rate_used": self.exchange_rate,
            "pricing_timestamp": datetime.now().isoformat()
        }