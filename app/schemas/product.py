from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime

# 👇 Reusable base schema for a pricing tier
class ProductPricingTierBase(BaseModel):
    moq: int  # Minimum Order Quantity
    price: float

# 👇 Used when creating a product
class ProductPricingTierCreate(ProductPricingTierBase):
    pass

# 👇 Used in the response when returning a product
class ProductPricingTierOut(ProductPricingTierBase):
    id: int

    class Config:
        from_attributes = True  # Replaces 'orm_mode' in Pydantic v2

# 👇 Base structure for a product (common fields)
class ProductBase(BaseModel):
    name: str
    description: str
    category: str
    stock: int
    price: float = 0.0  # Default price if not provided
    image_urls: List   # Corrected syntax for List[str]

    class Config:
        orm_mode = True

# 👇 This is what the vendor sends to create a product
class ProductCreate(ProductBase):
    pricing_tiers: List[ProductPricingTierCreate]

# 👇 This is what the API returns when fetching products
class ProductOut(ProductBase):
    id: int
    vendor_id: int
    created_at: datetime
    pricing_tiers: List[ProductPricingTierOut]

    class Config:
        from_attributes = True

# 👇 This is used for updating a product
class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    stock: Optional[int] = None
    price: Optional[float] = None
    pricing_tiers: Optional[List[Dict[str, Any]]] = None
    image_urls: Optional[List[str]] = None
    class Config:
        from_attributes = True
