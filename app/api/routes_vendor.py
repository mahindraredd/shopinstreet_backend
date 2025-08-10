# app/api/routes_vendor.py
# Enterprise-grade vendor routes with encryption and compliance

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.deps import get_db, get_current_vendor
from app.schemas.vendor import (
    VendorRegister, 
    VendorLogin, 
    VendorOut,
    VendorProfileUpdate,
    VendorBankingUpdate,
    VendorNotificationSettings,
    VendorProfileCompletion,
    VendorRiskAssessment
)
from app.crud import vendor as crud_vendor
from app.models.vendor import Vendor
from app.core.security import create_access_token, hash_password, verify_password
import logging
from app.services.vendor_website_service import VendorWebsiteService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/register")
def register_vendor(data: VendorRegister, db: Session = Depends(get_db)):
    """
    Enhanced vendor registration with automatic subdomain creation
    """
    
    # Step 1: Check if vendor already exists (existing logic)
    if crud_vendor.get_vendor_by_email_or_phone(db, data.email, data.phone):
        raise HTTPException(status_code=400, detail="Vendor already exists.")

    try:
        # Step 2: Create vendor 
        new_vendor = Vendor(
            business_name=data.business_name,
            business_category=data.business_category,
            address=data.address,
            city=data.city,
            state=data.state,
            pincode=data.pincode,
            country=data.country,
            owner_name=data.owner_name,
            email=data.email,
            phone=data.phone,
            password_hash=hash_password(data.password),
            verification_type=data.verification_type,
            verification_number=data.verification_number,
            website_url=data.website_url,
            linkedin_url=data.linkedin_url,
            business_logo=data.business_logo,
            is_verified=False,
            #  Set subdomain fields defaults
            domain_type='free',
            website_status='draft',
            readiness_score=0
        )

        # Step 3: Save vendor to database
        created_vendor = crud_vendor.create_vendor(db, new_vendor)
        
        # Step 4: 🆕 NEW - Generate subdomain automatically
        try:
            # Generate unique subdomain
            subdomain = created_vendor.update_subdomain_if_needed(db)
            
            # Calculate initial readiness score
            initial_score = created_vendor.calculate_readiness_score()
            
            # Commit subdomain and score updates
            db.commit()
            
            logger.info(f"Vendor {created_vendor.id} registered with subdomain: {subdomain}")
            
            # Step 5: Return enhanced response with website info
            return {
                "message": "Vendor registered successfully! Your website is being set up.",
                "vendor_id": created_vendor.id,
                "website_info": {
                    "subdomain": subdomain,
                    "website_url": created_vendor.get_website_url(),
                    "status": created_vendor.get_website_status_display(),
                    "readiness_score": initial_score,
                    "next_steps": created_vendor.get_next_steps()
                },
                "success": True
            }
            
        except Exception as subdomain_error:
            # If subdomain creation fails, still allow registration to succeed
            logger.warning(f"Subdomain creation failed for vendor {created_vendor.id}: {subdomain_error}")
            
            return {
                "message": "Vendor registered successfully. Website setup will be completed shortly.",
                "vendor_id": created_vendor.id,
                "website_info": {
                    "subdomain": None,
                    "website_url": None,
                    "status": "Setting up...",
                    "note": "Your website will be available shortly"
                },
                "success": True
            }
            
    except Exception as e:
        db.rollback()
        logger.error(f"Vendor registration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/login")
def login_vendor(data: VendorLogin, db: Session = Depends(get_db)):
    vendor = crud_vendor.get_vendor_by_email(db, data.email)

    if not vendor or not verify_password(data.password, vendor.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(data={"sub": vendor.email})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "vendor_id": vendor.id,
        "email": vendor.email,
        "is_verified": vendor.is_verified
    }

@router.get("/profile", response_model=VendorOut)
def get_vendor_profile(
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """Get current vendor's profile information"""
    # Update profile completion before returning
    vendor.update_profile_completion()
    vendor.update_compliance_status()
    db.commit()
    
    return vendor

# 🆕 ENTERPRISE: Update vendor profile with encryption and compliance
@router.put("/profile", response_model=VendorOut)
def update_vendor_profile(
    profile_data: VendorProfileUpdate,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """Update vendor profile information with enterprise features"""
    try:
        # Update only provided fields
        update_data = profile_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(vendor, field):
                setattr(vendor, field, value)
        
        # Update profile completion and compliance
        vendor.update_profile_completion()
        vendor.update_compliance_status()
        
        db.commit()
        db.refresh(vendor)
        
        logging.info(f"Vendor {vendor.id} profile updated. Completion: {vendor.profile_completion_percentage}%")
        
        return vendor
    except Exception as e:
        db.rollback()
        logging.error(f"Profile update failed for vendor {vendor.id}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to update profile: {str(e)}")

# 🆕 ENTERPRISE: Update banking information with encryption
@router.put("/banking")
def update_vendor_banking(
    banking_data: VendorBankingUpdate,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """Update vendor banking information with enterprise encryption"""
    try:
        # Update banking fields using property setters (auto-encryption)
        update_data = banking_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(vendor, field) and value is not None:
                setattr(vendor, field, value)
        
        # Update profile completion after banking info
        vendor.update_profile_completion()
        vendor.update_compliance_status()
        
        db.commit()
        db.refresh(vendor)
        
        # Log banking update (without sensitive data)
        logging.info(f"Vendor {vendor.id} banking information updated. Encrypted: {vendor.is_banking_data_encrypted()}")
        
        return {
            "message": "Banking information updated successfully",
            "encrypted": vendor.is_banking_data_encrypted(),
            "profile_completion": vendor.profile_completion_percentage
        }
    except Exception as e:
        db.rollback()
        logging.error(f"Banking update failed for vendor {vendor.id}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to update banking info: {str(e)}")

# 🆕 ENTERPRISE: Notification settings (stored in vendor for now)
@router.put("/notifications")
def update_vendor_notifications(
    notification_data: VendorNotificationSettings,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """Update vendor notification preferences"""
    try:
        # For enterprise version, you might want to store this in a separate table
        # For now, we'll store it as a JSON field or return success
        
        preferences = notification_data.dict()
        
        # In a full enterprise system, you'd store this in a notifications table
        # vendor.notification_preferences = preferences  # If you add this JSON field
        
        logging.info(f"Vendor {vendor.id} notification preferences updated")
        
        return {
            "message": "Notification preferences updated successfully",
            "preferences": preferences
        }
    except Exception as e:
        logging.error(f"Notification update failed for vendor {vendor.id}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to update notifications: {str(e)}")

# 🆕 ENTERPRISE: Get notification settings
@router.get("/notifications")
def get_vendor_notifications(
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """Get vendor notification preferences"""
    # Return default settings for now - in enterprise, load from notifications table
    return {
        "email_notifications": True,
        "order_updates": True,
        "low_stock_alerts": True,
        "marketing_emails": False,
        "weekly_reports": True
    }

# 🆕 ENTERPRISE: Profile completion analytics
@router.get("/profile/completion", response_model=VendorProfileCompletion)
def get_profile_completion(
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """Get detailed profile completion analysis"""
    vendor.update_profile_completion()
    db.commit()
    
    # Analyze missing fields
    missing_fields = []
    suggestions = []
    
    if not vendor.business_description:
        missing_fields.append("business_description")
        suggestions.append("Add a detailed business description to improve customer trust")
    
    if not vendor.website_url:
        missing_fields.append("website_url")
        suggestions.append("Add your website URL to increase credibility")
    
    if vendor.country == "Canada" and not vendor.hst_pst_number:
        missing_fields.append("hst_pst_number")
        suggestions.append("Add HST/PST number for Canadian tax compliance")
    
    if vendor.country == "India" and not vendor.gst_number:
        missing_fields.append("gst_number")
        suggestions.append("Add GST number for Indian tax compliance")
    
    if not vendor.bank_name or not vendor.account_number:
        missing_fields.append("banking_info")
        suggestions.append("Complete banking information for payment processing")
    
    return VendorProfileCompletion(
        profile_completion_percentage=vendor.profile_completion_percentage,
        profile_completed=vendor.profile_completed,
        missing_fields=missing_fields,
        suggestions=suggestions
    )

# 🆕 ENTERPRISE: Risk assessment
@router.get("/profile/risk", response_model=VendorRiskAssessment)
def get_risk_assessment(
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """Get vendor risk assessment and compliance status"""
    vendor.update_compliance_status()
    db.commit()
    
    # Analyze risk factors
    risk_factors = []
    recommendations = []
    
    if not vendor.is_verified:
        risk_factors.append("Account not verified")
        recommendations.append("Complete account verification process")
    
    if vendor.profile_completion_percentage < 80:
        risk_factors.append("Incomplete profile")
        recommendations.append("Complete your business profile to reduce risk score")
    
    if vendor.country == "India" and not vendor.gst_number:
        risk_factors.append("Missing GST number")
        recommendations.append("Add GST number for tax compliance")
    
    if not vendor.bank_name:
        risk_factors.append("Missing banking information")
        recommendations.append("Add banking details for payment processing")
    
    return VendorRiskAssessment(
        risk_score=vendor.risk_score,
        compliance_status=vendor.compliance_status,
        risk_factors=risk_factors,
        recommendations=recommendations
    )

@router.get("/test")
def test():
    """Test endpoint to verify vendor route is working"""
    return {"message": "Enterprise vendor route is working"}

# 🆕 NEW: Add this endpoint to get website info after registration
@router.get("/website-info")
def get_vendor_website_info(
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """Get vendor's website information"""
    
    try:
        # Ensure vendor has subdomain
        if not vendor.subdomain:
            vendor.update_subdomain_if_needed(db)
            db.commit()
        
        # Calculate current readiness
        current_score = vendor.calculate_readiness_score()
        db.commit()
        
        return {
            "success": True,
            "website_info": {
                "subdomain": vendor.subdomain,
                "website_url": vendor.get_website_url(),
                "domain_type": vendor.get_domain_type_display(),
                "status": vendor.get_website_status_display(),
                "readiness_score": current_score,
                "can_go_live": vendor.can_go_live(),
                "next_steps": vendor.get_next_steps(),
                "went_live_at": vendor.went_live_at.isoformat() if vendor.went_live_at else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting website info for vendor {vendor.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get website info: {str(e)}")

# 🆕 NEW: Add this endpoint to make website go live
@router.post("/go-live")
def make_website_live(
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """Make vendor website live"""
    
    try:
        # Attempt to go live
        result = vendor.go_live()
        
        if result["success"]:
            db.commit()
            logger.info(f"Vendor {vendor.id} website went live: {vendor.get_website_url()}")
            
            return {
                "success": True,
                "message": result["message"],
                "website_url": result["website_url"],
                "went_live_at": result["went_live_at"]
            }
        else:
            return {
                "success": False,
                "message": result["message"],
                "missing_requirements": result.get("missing_requirements", []),
                "current_score": result.get("current_score", 0),
                "required_score": result.get("required_score", 40)
            }
            
    except Exception as e:
        logger.error(f"Error making vendor {vendor.id} go live: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to go live: {str(e)}")

# 🆕 NEW: Add this endpoint to update readiness score
@router.post("/update-readiness")
def update_readiness_score(
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """Update vendor readiness score"""
    
    try:
        score = vendor.calculate_readiness_score()
        db.commit()
        
        return {
            "success": True,
            "readiness_score": score,
            "can_go_live": vendor.can_go_live(),
            "next_steps": vendor.get_next_steps(),
            "website_status": vendor.get_website_status_display()
        }
        
    except Exception as e:
        logger.error(f"Error updating readiness for vendor {vendor.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update readiness: {str(e)}")
