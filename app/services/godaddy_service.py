import requests
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from app.core.config import settings
from app.services.domain_config import DomainConfig

logger = logging.getLogger(__name__)

class GoDaddyService:
    """Production-ready GoDaddy API integration"""
    
    def __init__(self):
        self.api_key = settings.GODADDY_API_KEY
        self.api_secret = settings.GODADDY_API_SECRET
        self.environment = settings.GODADDY_ENVIRONMENT
        
        # Set API endpoint based on environment
        if self.environment == "PRODUCTION":
            self.base_url = "https://api.godaddy.com"
        else:
            self.base_url = "https://api.ote-godaddy.com"  # OTE test environment
        
        self.headers = {
            "Authorization": f"sso-key {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        logger.info(f"GoDaddy service initialized - Environment: {self.environment}")
    
    def check_domain_availability(self, domain: str) -> Dict:
        """Check if domain is available for registration"""
        try:
            url = f"{self.base_url}/v1/domains/available"
            params = {"domain": domain}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    "available": data.get("available", False),
                    "domain": domain,
                    "price": data.get("price", 0) * 83,  # Convert USD to INR
                    "currency": "INR",
                    "period": data.get("period", 1),
                    "definitive": data.get("definitive", False),
                    "checked_at": datetime.utcnow().isoformat()
                }
            else:
                logger.error(f"GoDaddy availability check failed: {response.status_code} - {response.text}")
                return {
                    "available": False,
                    "error": f"API Error: {response.status_code}",
                    "domain": domain
                }
        
        except requests.RequestException as e:
            logger.error(f"GoDaddy API request failed: {e}")
            return {
                "available": False,
                "error": f"Connection error: {str(e)}",
                "domain": domain
            }
        except Exception as e:
            logger.error(f"Unexpected error in domain availability check: {e}")
            return {
                "available": False,
                "error": f"Unexpected error: {str(e)}",
                "domain": domain
            }
    
    def register_domain(self, domain: str, contact_info: Dict, years: int = 1) -> Dict:
        """Register domain with GoDaddy"""
        try:
            url = f"{self.base_url}/v1/domains/purchase"
            
            # Prepare registration data
            registration_data = {
                "domain": domain,
                "period": years,
                "nameServers": [
                    "ns1.vision.com",
                    "ns2.vision.com"
                ],
                "renewAuto": True,
                "privacy": False,  # Can be enabled later
                "contacts": {
                    "registrant": self._format_contact(contact_info),
                    "admin": self._format_contact(contact_info),
                    "tech": self._format_contact(contact_info),
                    "billing": self._format_contact(contact_info)
                }
            }
            
            response = requests.post(
                url, 
                headers=self.headers, 
                json=registration_data, 
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    "success": True,
                    "domain": domain,
                    "order_id": data.get("orderId"),
                    "status": "registered",
                    "expiry_date": (datetime.utcnow() + timedelta(days=365*years)).isoformat(),
                    "nameservers": registration_data["nameServers"],
                    "registration_id": data.get("orderId")
                }
            else:
                error_msg = self._parse_godaddy_error(response)
                logger.error(f"GoDaddy domain registration failed: {error_msg}")
                
                return {
                    "success": False,
                    "error": error_msg,
                    "domain": domain,
                    "status_code": response.status_code
                }
        
        except requests.RequestException as e:
            logger.error(f"GoDaddy registration request failed: {e}")
            return {
                "success": False,
                "error": f"Connection error: {str(e)}",
                "domain": domain
            }
        except Exception as e:
            logger.error(f"Unexpected error in domain registration: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "domain": domain
            }
    
    def get_domain_details(self, domain: str) -> Dict:
        """Get details of registered domain"""
        try:
            url = f"{self.base_url}/v1/domains/{domain}"
            
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    "success": True,
                    "domain": domain,
                    "status": data.get("status"),
                    "created_at": data.get("createdAt"),
                    "expires": data.get("expires"),
                    "nameservers": data.get("nameServers", []),
                    "locked": data.get("locked", False),
                    "privacy": data.get("privacy", False)
                }
            else:
                return {
                    "success": False,
                    "error": f"Domain not found or API error: {response.status_code}",
                    "domain": domain
                }
        
        except Exception as e:
            logger.error(f"Error getting domain details: {e}")
            return {
                "success": False,
                "error": str(e),
                "domain": domain
            }
    
    def update_nameservers(self, domain: str, nameservers: List[str]) -> Dict:
        """Update nameservers for domain"""
        try:
            url = f"{self.base_url}/v1/domains/{domain}/records/@/NS"
            
            ns_records = [{"data": ns, "ttl": 3600} for ns in nameservers]
            
            response = requests.put(
                url,
                headers=self.headers,
                json=ns_records,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "domain": domain,
                    "nameservers": nameservers,
                    "message": "Nameservers updated successfully"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to update nameservers: {response.status_code}",
                    "domain": domain
                }
        
        except Exception as e:
            logger.error(f"Error updating nameservers: {e}")
            return {
                "success": False,
                "error": str(e),
                "domain": domain
            }
    
    def _format_contact(self, contact_info: Dict) -> Dict:
        """Format contact information for GoDaddy API"""
        return {
            "nameFirst": contact_info.get("name", "").split()[0] if contact_info.get("name") else "Unknown",
            "nameLast": contact_info.get("name", "").split()[-1] if contact_info.get("name") else "User",
            "email": contact_info.get("email", "contact@example.com"),
            "phone": contact_info.get("phone", "+91.9999999999"),
            "organization": contact_info.get("organization", ""),
            "addressMailing": {
                "address1": contact_info.get("address", "Unknown Address"),
                "city": contact_info.get("city", "Mumbai"),
                "state": contact_info.get("state", "Maharashtra"),
                "postalCode": contact_info.get("postal_code", "400001"),
                "country": contact_info.get("country", "IN")
            }
        }
    
    def _parse_godaddy_error(self, response) -> str:
        """Parse GoDaddy API error response"""
        try:
            error_data = response.json()
            if "message" in error_data:
                return error_data["message"]
            elif "errors" in error_data and len(error_data["errors"]) > 0:
                return error_data["errors"][0].get("message", "Unknown error")
            else:
                return f"API Error: {response.status_code}"
        except:
            return f"API Error: {response.status_code} - {response.text[:100]}"
    
    def test_connection(self) -> Dict:
        """Test GoDaddy API connection"""
        try:
            url = f"{self.base_url}/v1/domains/available"
            params = {"domain": "test123456789.com"}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "environment": self.environment,
                    "endpoint": self.base_url,
                    "message": "GoDaddy API connection successful"
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}",
                    "environment": self.environment
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "environment": self.environment
            }