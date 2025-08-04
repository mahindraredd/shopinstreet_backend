# app/services/domain_service.py
import re
from typing import List, Dict

class DomainService:
    """Simple domain suggestion service"""
    
    @staticmethod
    def generate_domain_suggestions(business_name: str, max_suggestions: int = 12) -> List[Dict]:
        """Generate domain suggestions based on business name"""
        
        # Clean business name
        clean_name = DomainService._clean_business_name(business_name)
        
        # Generate variations
        variations = DomainService._generate_name_variations(clean_name)
        
        # Get TLD options with pricing
        tlds = DomainService._get_tld_options()
        
        suggestions = []
        
        # Generate suggestions for each variation + TLD combination
        for variation in variations:
            for tld in tlds:
                if len(suggestions) >= max_suggestions:
                    break
                    
                domain = f"{variation}.{tld['ext']}"
                
                suggestion = {
                    "suggested_domain": domain,
                    "tld": tld["ext"],
                    "registration_price": tld["price"],
                    "renewal_price": tld["renewal_price"],
                    "is_popular_tld": tld["popular"],
                    "recommendation_score": DomainService._calculate_recommendation_score(
                        variation, tld, clean_name
                    ),
                    "is_available": True,  # For now, assume all are available
                    "is_premium": False
                }
                
                suggestions.append(suggestion)
        
        # Sort by recommendation score (highest first)
        suggestions.sort(key=lambda x: x["recommendation_score"], reverse=True)
        
        return suggestions[:max_suggestions]
    
    @staticmethod
    def _clean_business_name(business_name: str) -> str:
        """Clean business name for domain generation"""
        # Remove common business suffixes
        suffixes = ['llc', 'inc', 'corp', 'ltd', 'co', 'company', 'business', 'shop', 'store']
        
        # Convert to lowercase and remove special characters
        clean = re.sub(r'[^a-zA-Z0-9\s]', '', business_name.lower())
        
        # Remove business suffixes
        words = clean.split()
        filtered_words = [w for w in words if w not in suffixes]
        
        if not filtered_words:  # If all words were suffixes, use original
            filtered_words = words
        
        return ''.join(filtered_words)
    
    @staticmethod
    def _generate_name_variations(clean_name: str) -> List[str]:
        """Generate variations of the business name for domains"""
        variations = [clean_name]
        
        # Add common prefixes/suffixes for e-commerce
        prefixes = ['get', 'buy', 'shop', 'my']
        suffixes = ['shop', 'store', 'online', 'hub']
        
        # Add prefixed variations (keep domains reasonable length)
        for prefix in prefixes:
            if len(clean_name) <= 10:
                variations.append(f"{prefix}{clean_name}")
        
        # Add suffixed variations
        for suffix in suffixes:
            if len(clean_name) <= 12:
                variations.append(f"{clean_name}{suffix}")
        
        return variations[:6]  # Limit variations
    
    @staticmethod
    def _get_tld_options() -> List[Dict]:
        """Get available TLD options with pricing"""
        return [
            {"ext": "com", "price": 12.99, "renewal_price": 12.99, "popular": True},
            {"ext": "net", "price": 14.99, "renewal_price": 14.99, "popular": False},
            {"ext": "shop", "price": 39.99, "renewal_price": 39.99, "popular": True},
            {"ext": "store", "price": 59.99, "renewal_price": 59.99, "popular": False},
            {"ext": "co", "price": 29.99, "renewal_price": 29.99, "popular": True},
        ]
    
    @staticmethod
    def _calculate_recommendation_score(variation: str, tld: Dict, original_name: str) -> float:
        """Calculate recommendation score for domain suggestion"""
        score = 0.0
        
        # Preference for popular TLDs
        if tld["popular"]:
            score += 0.3
        
        # Preference for .com
        if tld["ext"] == "com":
            score += 0.4
        
        # Preference for shorter domains
        domain_length = len(variation)
        if domain_length <= 8:
            score += 0.3
        elif domain_length <= 12:
            score += 0.2
        
        # Preference for exact match with business name
        if variation == original_name:
            score += 0.4
        
        # Bonus for e-commerce friendly terms
        ecommerce_terms = ['shop', 'store', 'buy', 'get']
        if any(term in variation for term in ecommerce_terms):
            score += 0.1
        
        return min(1.0, score)  # Cap at 1.0