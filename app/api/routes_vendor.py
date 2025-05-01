from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.vendor import VendorRegister, VendorLogin
from app.models.vendor import Vendor
from app.core.security import create_access_token, hash_password, verify_password
from app.db.deps import get_db
from app.crud import vendor as crud_vendor

router = APIRouter()

@router.post("/register")
def register_vendor(data: VendorRegister, db: Session = Depends(get_db)):
    if crud_vendor.get_vendor_by_email_or_phone(db, data.email, data.phone):
        raise HTTPException(status_code=400, detail="Vendor already exists.")

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
        is_verified=False
    )

    created_vendor = crud_vendor.create_vendor(db, new_vendor)
    return {"message": "Vendor registered successfully. Pending verification."}

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



@router.get("/test")
def test():
    """Test endpoint to verify product route is working"""
    return {"message": "Product route is working"}