# app/api/routes_domain.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.deps import get_db, get_current_vendor
from app.services.domain_service import DomainService
from app.models.vendor import Vendor
from app.schemas.domain import DomainSuggestionOut, DomainSuggestionResponse

router = APIRouter()

@router.get("/suggestions/{business_name}", response_model=DomainSuggestionResponse)
async def get_domain_suggestions(
    business_name: str,
    max_results: int = Query(12, ge=1, le=20),
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """
    Get domain suggestions based on business name
    
    - **business_name**: The business name to generate suggestions for
    - **max_results**: Maximum number of suggestions to return (1-20)
    """
    try:
        if not business_name or len(business_name.strip()) < 2:
            raise HTTPException(
                status_code=400, 
                detail="Business name must be at least 2 characters long"
            )
        
        suggestions = DomainService.generate_domain_suggestions(
            business_name=business_name.strip(),
            max_suggestions=max_results
        )
        
        return DomainSuggestionResponse(
            suggestions=[DomainSuggestionOut(**suggestion) for suggestion in suggestions],
            business_name=business_name.strip(),
            total_suggestions=len(suggestions)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate domain suggestions: {str(e)}"
        )

@router.get("/test")
async def test_domain_endpoint():
    """Test endpoint to verify domain routes are working"""
    return {
        "message": "Domain API is working!",
        "endpoints": [
            "GET /suggestions/{business_name} - Get domain suggestions"
        ]
    }