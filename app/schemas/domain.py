# app/schemas/domain.py
from pydantic import BaseModel
from typing import List
from datetime import datetime

class DomainSuggestionOut(BaseModel):
    suggested_domain: str
    tld: str
    registration_price: float
    renewal_price: float
    is_available: bool
    is_premium: bool
    is_popular_tld: bool
    recommendation_score: float
    
    class Config:
        from_attributes = True

class DomainSuggestionResponse(BaseModel):
    suggestions: List[DomainSuggestionOut]
    business_name: str
    total_suggestions: int