from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# ✅ Used for Register endpoint (incoming data)
class VendorRegister(BaseModel):
    business_name: str
    business_category: str
    address: str
    city: str
    state: str
    pincode: str
    country: str
    owner_name: str
    email: EmailStr
    phone: str
    password: str
    verification_type: str
    verification_number: str
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    business_logo: Optional[str] = None

# ✅ Used for Login endpoint
class VendorLogin(BaseModel):
    email: EmailStr
    password: str

# ✅ UPDATED: Complete vendor response schema with address fields
class VendorOut(BaseModel):
    id: int
    email: EmailStr
    business_name: str
    business_category: str
    address: str
    city: str
    state: str
    pincode: str
    country: str
    owner_name: str
    phone: str
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    business_logo: Optional[str] = None
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True  # ✅ Pydantic v2 format