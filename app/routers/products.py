from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy.orm import joinedload
from app.db.deps import get_db
from app.models import models
from app.schemas.schemas import ProductCreate, ProductOut

router = APIRouter()


@router.post("/", response_model=List[ProductOut])
def create_products(products: List[ProductCreate], db: Session = Depends(get_db)):
    created_products = []

    for product in products:
        db_product = models.Product(
            name=product.name,
            description=product.description,
            category=product.category,
            image_url=product.image_url,
            available_quantity=product.available_quantity,
        )
        db.add(db_product)
        db.commit()
        db.refresh(db_product)

        for tier in product.pricing_tiers:
            pricing = models.PricingTier(
                product_id=db_product.id,
                moq=tier.moq,
                price=tier.price
            )
            db.add(pricing)
        db.commit()

        created_products.append(db_product)

    return created_products

@router.get("/", response_model=List[ProductOut])
def get_products(db: Session = Depends(get_db)):
    products = db.query(models.Product).options(joinedload(models.Product.pricing_tiers)).all()

    # Attach only the price for MOQ=1
    product_list = []
    for product in products:
        price_for_moq1 = None
        for tier in product.pricing_tiers:
            if tier.moq == 1:
                price_for_moq1 = tier.price
                break  
        product_dict = {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "category": product.category,
            "image_url": product.image_url,
            "available_quantity": product.available_quantity,
            "price": price_for_moq1,
            "pricing_tiers": [],
        }
        product_list.append(product_dict)
        print(product_list)
    return product_list



@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product