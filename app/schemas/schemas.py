from pydantic import BaseModel, EmailStr
from typing import List

class UserSignup(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr

    class Config:
        from_attributes = True

class ShippingInfo(BaseModel):
    full_name: str
    address: str
    city: str
    state: str
    pincode: str
    country: str
    phone: str
    email: EmailStr

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    id: int
    name: str
    email: str
    
class CartItemCreate(BaseModel):
    product_id: int
    quantity: int

class PricingTierBase(BaseModel):
    moq: int
    price: int


class PricingTierCreate(PricingTierBase):
    pass


class PricingTierOut(PricingTierBase):
    id: int
    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str
    description: str
    category: str
    image_url: str
    available_quantity: int
    pricing_tiers: List[PricingTierCreate]


from typing import Optional

class ProductOut(BaseModel):
    id: int
    name: str
    description: str
    category: str
    image_url: str
    available_quantity: int
    price: Optional[int] = None  # Make price optional
    pricing_tiers: List[PricingTierOut]

    class Config:
        from_attributes = True

