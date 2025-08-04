# app/api/routes_business_profile.py - Simplified Working Version

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from app.db.deps import get_db, get_current_vendor
from app.models.vendor import Vendor
from app.services.business_profile_service import BusinessProfileService
from app.schemas.business_profile import (
    BusinessProfileResponse,
    BusinessProfileUpdateRequest,
    BankingInfoUpdateRequest,
    ProfileCompletionResponse,
    ComplianceStatusResponse,
    CountryRequirementsResponse,
    FieldValidationResponse,
    SuccessResponse,
    ErrorResponse
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/business-profile", tags=["Business Profile"])

@router.get("/test")
async def test_business_profile_api():
    """Test endpoint for business profile API"""
    return {
        "success": True,
        "message": "Business Profile API is working!",
        "version": "1.0",
        "features": [
            "Profile management",
            "Banking encryption", 
            "Compliance tracking",
            "Field validation"
        ]
    }

@router.get(
    "/",
    response_model=BusinessProfileResponse,
    summary="Get Business Profile"
)
async def get_business_profile(
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Get complete business profile for authenticated vendor"""
    try:
        # Get fresh profile data
        profile = BusinessProfileService.get_business_profile(db, vendor.id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business profile not found"
            )
        
        # Mask sensitive data for response
        profile_data = BusinessProfileService.mask_sensitive_data(profile)
        
        return BusinessProfileResponse(**profile_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting business profile for vendor {vendor.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve business profile"
        )

@router.put(
    "/",
    response_model=BusinessProfileResponse,
    summary="Update Business Profile"
)
async def update_business_profile(
    profile_update: BusinessProfileUpdateRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Update business profile information"""
    try:
        # For now, just return the current profile
        # We'll implement the update logic later
        profile = BusinessProfileService.get_business_profile(db, vendor.id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business profile not found"
            )
        
        # Return masked data
        profile_data = BusinessProfileService.mask_sensitive_data(profile)
        
        logger.info(f"Business profile update requested for vendor {vendor.id}")
        return BusinessProfileResponse(**profile_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating business profile for vendor {vendor.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update business profile"
        )

@router.put(
    "/banking",
    summary="Update Banking Information"
)
async def update_banking_info(
    banking_update: BankingInfoUpdateRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Update sensitive banking information"""
    try:
        logger.info(f"Banking information update requested for vendor {vendor.id}")
        return {
            "success": True,
            "message": "Banking information update endpoint - coming soon!",
            "data": {
                "vendor_id": vendor.id,
                "bank_name": banking_update.bank_name
            }
        }
        
    except Exception as e:
        logger.error(f"Error updating banking info for vendor {vendor.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update banking information"
        )

@router.get(
    "/completion-status",
    summary="Get Profile Completion Status"
)
async def get_profile_completion_status(
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Get profile completion status"""
    try:
        return {
            "completion_percentage": 45,
            "is_profile_complete": False,
            "completed_sections": ["Basic Information", "Contact Information"],
            "missing_sections": ["Banking Information", "Tax Information"],
            "next_recommended_action": "Complete banking information",
            "priority_missing_fields": ["bank_name", "account_number"]
        }
        
    except Exception as e:
        logger.error(f"Error getting completion status for vendor {vendor.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get profile completion status"
        )

@router.get(
    "/compliance-status",
    summary="Get Compliance Status"
)
async def get_compliance_status(
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Get compliance status"""
    try:
        return {
            "risk_score": 50,
            "compliance_status": "pending",
            "last_check": None,
            "compliance_issues": ["Missing banking information", "Profile incomplete"],
            "recommendations": ["Complete banking details", "Add business description"]
        }
        
    except Exception as e:
        logger.error(f"Error getting compliance status for vendor {vendor.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get compliance status"
        )

@router.get(
    "/country-requirements",
    summary="Get Country Requirements"
)
async def get_country_requirements(
    country: str = Query(..., description="Country name"),
    vendor: Vendor = Depends(get_current_vendor)
):
    """Get country-specific requirements"""
    try:
        # Simple country requirements
        requirements = {
            "India": {
                "country": "India",
                "required_tax_fields": ["gst_number", "pan_card"],
                "optional_tax_fields": ["business_registration_number"],
                "banking_requirements": {
                    "routing_code": "IFSC Code (11 characters)",
                    "account_number": "10-18 digit account number"
                },
                "sample_formats": {
                    "gst_number": "22AAAAA0000A1Z5",
                    "pan_card": "ABCDE1234F"
                },
                "supported_currencies": ["INR", "USD"]
            },
            "Canada": {
                "country": "Canada",
                "required_tax_fields": ["hst_pst_number"],
                "optional_tax_fields": ["business_registration_number"],
                "banking_requirements": {
                    "routing_code": "9-digit routing number",
                    "account_number": "7-12 digit account number"
                },
                "sample_formats": {
                    "hst_pst_number": "123456789RT0001"
                },
                "supported_currencies": ["CAD", "USD"]
            }
        }
        
        return requirements.get(country, {
            "country": country,
            "required_tax_fields": [],
            "optional_tax_fields": [],
            "banking_requirements": {},
            "sample_formats": {},
            "supported_currencies": ["USD"]
        })
        
    except Exception as e:
        logger.error(f"Error getting country requirements for {country}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get country requirements"
        )

@router.post(
    "/validate-field",
    summary="Validate Field"
)
async def validate_field(
    field_name: str = Query(..., description="Field name to validate"),
    field_value: str = Query(..., description="Field value to validate"),
    country: str = Query("United States", description="Country for validation"),
    vendor: Vendor = Depends(get_current_vendor)
):
    """Validate individual field values"""
    try:
        # Simple validation
        is_valid = len(field_value.strip()) > 0
        
        return {
            "field_name": field_name,
            "is_valid": is_valid,
            "error_message": None if is_valid else f"{field_name} cannot be empty",
            "suggestions": [] if is_valid else [f"Please enter a valid {field_name}"]
        }
        
    except Exception as e:
        logger.error(f"Error validating field {field_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate field"
        )

@router.post(
    "/refresh-compliance",
    summary="Refresh Compliance Status"
)
async def refresh_compliance_status(
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Manually refresh compliance status"""
    try:
        logger.info(f"Compliance status refresh requested for vendor {vendor.id}")
        
        return {
            "risk_score": 45,
            "compliance_status": "pending",
            "last_check": "2025-07-30T23:30:00Z",
            "compliance_issues": ["Profile incomplete"],
            "recommendations": ["Complete business profile information"]
        }
        
    except Exception as e:
        logger.error(f"Error refreshing compliance status for vendor {vendor.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh compliance status"
        )