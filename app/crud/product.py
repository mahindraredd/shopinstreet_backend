from typing import Optional, List
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.product import Product, ProductPricingTier
from app.schemas.product import ProductCreate, ProductUpdate

#  Create a product with pricing tiers
def create_product(db: Session, vendor_id: int, data: ProductCreate) -> Product:
    if not data.pricing_tiers:
        raise HTTPException(status_code=400, detail="At least one pricing tier is required")

    # Take the price from the first pricing tier
    first_price = data.pricing_tiers[0].price
    print(f"image_urls: {data.image_urls}")
    product = Product(
        name=data.name,
        description=data.description,
        category=data.category,
        image_urls=data.image_urls,
        stock=data.stock,
        vendor_id=vendor_id,
        price=first_price,  # Default price if not provided
    )
    db.add(product)
    db.flush()  # flush so product.id is available

    for tier in data.pricing_tiers:
        pricing = ProductPricingTier(
            moq=tier.moq,
            price=tier.price,
            product_id=product.id
        )
        db.add(pricing)

    db.commit()
    db.refresh(product)
    return product

#  Get all products by vendor
def get_products_by_vendor(db: Session, vendor_id: int, skip: int = 0, limit: int = 10):
    return db.query(Product).filter(Product.vendor_id == vendor_id).offset(skip).limit(limit).all()

#  Get all products (admin use-case)
def get_all_products(db: Session) -> List[Product]:
    return db.query(Product).all()

#  Get one product
def get_product_by_id(db: Session, product_id: int) -> Optional[Product]:
    return db.query(Product).filter(Product.id == product_id).first()

#  Update product
# Update the update_product function to handle pricing tiers
# Replace the update_product function in app/crud/product.py with this:

def update_product(db: Session, product_id: int, vendor_id: int, data: ProductUpdate) -> Optional[Product]:
    product = db.query(Product).filter(Product.id == product_id, Product.vendor_id == vendor_id).first()
    if not product:
        return None

    # Update simple fields
    update_data = data.model_dump(exclude={"pricing_tiers"}, exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    # Handle pricing tiers update if provided
    if data.pricing_tiers is not None:
        # Delete existing pricing tiers
        db.query(ProductPricingTier).filter(ProductPricingTier.product_id == product_id).delete()
        
        # Add new pricing tiers
        for tier in data.pricing_tiers:
            # Handle both dictionary and object access safely
            if isinstance(tier, dict):
                moq_value = tier.get("moq")
                price_value = tier.get("price")
            else:
                moq_value = getattr(tier, "moq", None)
                price_value = getattr(tier, "price", None)
            
            # Validate required values
            if moq_value is None:
                raise ValueError(f"Missing 'moq' in pricing tier: {tier}")
            if price_value is None:
                raise ValueError(f"Missing 'price' in pricing tier: {tier}")
            
            # Convert and validate types
            try:
                moq_int = int(moq_value)
                price_float = float(price_value)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid pricing tier values - moq: {moq_value}, price: {price_value}. Error: {e}")
            
            # Business validation
            if moq_int <= 0:
                raise ValueError(f"MOQ must be greater than 0, got: {moq_int}")
            if price_float <= 0:
                raise ValueError(f"Price must be greater than 0, got: {price_float}")
            
            pricing = ProductPricingTier(
                moq=moq_int,
                price=price_float,
                product_id=product_id
            )
            db.add(pricing)

    db.commit()
    db.refresh(product)
    return product
#  Delete product
def delete_product(db: Session, product_id: int, vendor_id: int) -> bool:
    product = db.query(Product).filter(Product.id == product_id, Product.vendor_id == vendor_id).first()
    if not product:
        return False

    db.delete(product)
    db.commit()
    return True


def search_products_by_vendor(db: Session, vendor_id: int, query: str) -> List[Product]:
    return (
        db.query(Product)
        .filter(
            Product.vendor_id == vendor_id,
            (Product.name.ilike(f"%{query}%")) | (Product.category.ilike(f"%{query}%"))
        )
        .all()
    )

# In app/crud/product.py

def update_product_images(db: Session, product_id: int, image_urls: List[str]):
    """Update product images - replaces all images with the provided list"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        # This replaces ALL images with the new list
        product.image_urls = image_urls
        db.commit()
        db.refresh(product)
    return product
