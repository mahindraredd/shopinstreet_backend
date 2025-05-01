import json
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from typing import List
from fastapi import Query

from app.schemas.product import ProductCreate, ProductOut
from app.crud import product as crud_product
from app.db.deps import get_db, get_current_vendor
from app.models.vendor import Vendor
from app.schemas.product import ProductUpdate
from app.services.image_service import generate_presigned_url, process_and_upload_images, process_and_upload_images1

router = APIRouter()

# 🔹 Test route
@router.get("/test")
def test():
    return {"message": "Product route is working"}

# ✅ Create product
@router.post("/", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product_route(
    name: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    stock: int = Form(...),
    price: float = Form(...),
    pricing_tiers: str = Form(...),  # received as stringified JSON
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor),
):
    """
    Create a new product for the current logged-in vendor.
    """
    try:
        # Parse pricing_tiers JSON
        pricing_tiers = json.loads(pricing_tiers)

        # Validate pricing_tiers format
        if not isinstance(pricing_tiers, list):
            raise ValueError("pricing_tiers must be a list of objects")

        # Upload images to S3
        image_urls = []  # Placeholder for image URLs
        for img in images:
            content = await img.read()
            cleaned_image = await process_and_upload_images1(content, vendor.id)
            if not isinstance(cleaned_image, str):
                raise ValueError("Image processing failed. Expected a URL string.")
            image_urls.append(cleaned_image)

        # Create ProductCreate schema
        product_data = ProductCreate(
            name=name,
            description=description,
            category=category,
            stock=stock,
            price=price,
            pricing_tiers=pricing_tiers,
            image_urls=image_urls,
        )

        # Save to DB
        created_product = crud_product.create_product(db=db, data=product_data, vendor_id=vendor.id)

        # Return the created product
        return ProductOut(
            id=created_product.id,
            vendor_id=created_product.vendor_id,
            name=created_product.name,
            description=created_product.description,
            category=created_product.category,
            stock=created_product.stock,
            price=created_product.price,
            pricing_tiers=created_product.pricing_tiers,
            image_urls=created_product.image_urls,
            created_at=created_product.created_at,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ✅ List current vendor's products
@router.get("/mine", response_model=List[ProductOut])
def list_my_products(
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """
    List paginated products belonging to the logged-in vendor.
    """
    skip = (page - 1) * size
    products = crud_product.get_products_by_vendor(db, vendor.id, skip=skip, limit=size)

    # 👇 Inject presigned URLs for each product's images
    for product in products:
        product.image_urls = [
            generate_presigned_url(key) for key in product.image_urls
        ]
    print(f"products: {products}")
    
    return products

# ✅ Optional: List all products from all vendors
@router.get("/all", response_model=List[ProductOut])
def list_all_products(db: Session = Depends(get_db)):
    """
    List all products in the system (Admin use case).
    """
    return crud_product.get_all_products(db)

@router.get("/{product_id}", response_model=ProductOut)
def get_product_by_id_route(
    product_id: int,
    db: Session = Depends(get_db)
):
    
    product = crud_product.get_product_by_id(db, product_id)
    product.image_urls = [
        generate_presigned_url(obj_key) for obj_key in product.image_urls
    ]
    print(f"product image urls: {product.image_urls}")
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.patch("/{product_id}", response_model=ProductOut)
def update_product_route(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    updated = crud_product.update_product(db, product_id, vendor.id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Product not found or unauthorized")
    return updated

@router.delete("/{product_id}", status_code=204)
def delete_product_route(
    product_id: int,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    success = crud_product.delete_product(db, product_id, vendor.id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found or unauthorized")
    return

@router.get("/mine/search", response_model=List[ProductOut])
def search_my_products(
    query: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """
    🔍 Search products by name or category (only for the logged-in vendor).
    """
    return crud_product.search_products_by_vendor(db, vendor.id, query)




