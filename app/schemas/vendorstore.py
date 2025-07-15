from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ProductPricingTierSchema(BaseModel):
    moq: int
    price: float

    class Config:
        from_attributes = True

class ProductSchema(BaseModel):
    id: int
    name: str
    description: str
    category: str
    image_urls: List[str]
    stock: int
    price: float
    pricing_tiers: List[ProductPricingTierSchema]

    class Config:
        from_attributes = True

class VendorStoreSchema(BaseModel):
    vendor_id: int
    business_name: str
    business_logo: Optional[str]
    categories: List[str]
    filters: dict
    products: List[ProductSchema]
    template_id: int = 1  # Default template is 1
    
    class Config:
        from_attributes = True

# Optional: Create a separate schema for template updates
class TemplateUpdateSchema(BaseModel):
    template_id: int
    
    class Config:
        from_attributes = True