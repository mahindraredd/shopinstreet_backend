from typing import Optional, List
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.product import Product, ProductPricingTier
from app.schemas.product import ProductCreate, ProductUpdate

# ✅ Create a product with pricing tiers
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

# ✅ Get all products by vendor
def get_products_by_vendor(db: Session, vendor_id: int, skip: int = 0, limit: int = 10):
    return db.query(Product).filter(Product.vendor_id == vendor_id).offset(skip).limit(limit).all()

# ✅ Get all products (admin use-case)
def get_all_products(db: Session) -> List[Product]:
    return db.query(Product).all()

# ✅ Get one product
def get_product_by_id(db: Session, product_id: int) -> Optional[Product]:
    return db.query(Product).filter(Product.id == product_id).first()

# ✅ Update product
def update_product(db: Session, product_id: int, vendor_id: int, data: ProductUpdate) -> Optional[Product]:
    product = db.query(Product).filter(Product.id == product_id, Product.vendor_id == vendor_id).first()
    if not product:
        return None

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product

# ✅ Delete product
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

def update_product_images(db: Session, product_id: int, image_urls: List[str]):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        product.image_urls = image_urls
        db.commit()
        db.refresh(product)
    return product

