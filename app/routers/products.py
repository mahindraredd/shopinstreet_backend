# Update your app/api/routes_product.py

import json
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import Query

from app.schemas.product import ProductCreate, ProductOut
from app.crud import product as crud_product
from app.db.deps import get_db, get_current_vendor
from app.models.vendor import Vendor
from app.schemas.product import ProductUpdate
from app.services.image_service import (
    generate_presigned_url, 
    process_and_upload_images, 
    process_and_upload_images1,
    get_presigned_urls_for_product
)

router = APIRouter()

# 🔹 Test route
@router.get("/test")
def test():
    return {"message": "Product route is working"}

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
    FIXED: Now properly returns presigned URLs in response
    """
    try:
        print(f"🏪 Creating product for vendor {vendor.id}: {name}")
        
        # Parse pricing_tiers JSON
        pricing_tiers_data = json.loads(pricing_tiers)
        print(f"📊 Pricing tiers: {pricing_tiers_data}")

        # Validate pricing_tiers format
        if not isinstance(pricing_tiers_data, list):
            raise ValueError("pricing_tiers must be a list of objects")

        # Upload images to S3 and get S3 keys (not URLs yet)
        print(f"📸 Processing {len(images)} images...")
        image_keys = []
        
        for i, img in enumerate(images):
            print(f"📸 Processing image {i+1}/{len(images)}: {img.filename}")
            content = await img.read()
            s3_key = await process_and_upload_images1(content, vendor.id)
            if not isinstance(s3_key, str):
                raise ValueError(f"Image {i+1} processing failed. Expected S3 key string.")
            image_keys.append(s3_key)
            print(f"✅ Image {i+1} uploaded with key: {s3_key}")

        print(f"✅ All images uploaded. Keys: {image_keys}")

        # Create ProductCreate object with S3 keys
        product_data = ProductCreate(
            name=name,
            description=description,
            category=category,
            stock=stock,
            price=price,
            image_urls=image_keys,  # Store S3 keys in database
            pricing_tiers=pricing_tiers_data
        )

        # Save product to database
        print(f"💾 Saving product to database...")
        created_product = crud_product.create_product(db, product_data, vendor.id)
        print(f"✅ Product saved with ID: {created_product.id}")
        
        # 🔧 CRITICAL FIX: Generate presigned URLs for the response
        print(f"🔗 Generating presigned URLs for response...")
        try:
            presigned_urls = get_presigned_urls_for_product(created_product.image_urls)
            print(f"✅ Generated {len(presigned_urls)} presigned URLs")
        except Exception as e:
            print(f"❌ Error generating presigned URLs: {e}")
            # Fallback: generate URLs manually
            presigned_urls = []
            for key in created_product.image_urls:
                try:
                    url = generate_presigned_url(key)
                    presigned_urls.append(url)
                except Exception as url_error:
                    print(f"❌ Failed to generate URL for key {key}: {url_error}")
                    # Skip this image rather than failing completely
                    continue
        
        # Create response with presigned URLs
        product_response = ProductOut(
            id=created_product.id,
            name=created_product.name,
            description=created_product.description,
            category=created_product.category,
            stock=created_product.stock,
            price=created_product.price,
            image_urls=presigned_urls,  # 🔧 FIXED: Return presigned URLs to frontend
            vendor_id=created_product.vendor_id,
            created_at=created_product.created_at,
            pricing_tiers=created_product.pricing_tiers
        )

        print(f"🎉 Product creation completed successfully!")
        print(f"📷 Returning {len(presigned_urls)} presigned URLs to frontend")
        
        return product_response

    except json.JSONDecodeError:
        print(f"❌ Invalid JSON format for pricing_tiers")
        raise HTTPException(status_code=400, detail="Invalid JSON format for pricing_tiers")
    except ValueError as ve:
        print(f"❌ Validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"❌ Error creating product: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")


# Alternative version if you don't have get_presigned_urls_for_product function:
@router.post("/alternative", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product_route_alternative(
    name: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    stock: int = Form(...),
    price: float = Form(...),
    pricing_tiers: str = Form(...),
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor),
):
    """
    Alternative create product endpoint if get_presigned_urls_for_product doesn't exist
    """
    try:
        print(f"🏪 Creating product for vendor {vendor.id}: {name}")
        
        # Parse pricing_tiers JSON
        pricing_tiers_data = json.loads(pricing_tiers)
        
        # Validate pricing_tiers format
        if not isinstance(pricing_tiers_data, list):
            raise ValueError("pricing_tiers must be a list of objects")

        # Upload images to S3 and get S3 keys
        print(f"📸 Processing {len(images)} images...")
        image_keys = []
        
        for i, img in enumerate(images):
            print(f"📸 Processing image {i+1}/{len(images)}: {img.filename}")
            content = await img.read()
            s3_key = await process_and_upload_images1(content, vendor.id)
            if not isinstance(s3_key, str):
                raise ValueError(f"Image {i+1} processing failed. Expected S3 key string.")
            image_keys.append(s3_key)
            print(f"✅ Image {i+1} uploaded with key: {s3_key}")

        print(f"✅ All images uploaded. Keys: {image_keys}")

        # Create ProductCreate object with S3 keys
        product_data = ProductCreate(
            name=name,
            description=description,
            category=category,
            stock=stock,
            price=price,
            image_urls=image_keys,  # Store S3 keys in database
            pricing_tiers=pricing_tiers_data
        )

        # Save product to database
        print(f"💾 Saving product to database...")
        created_product = crud_product.create_product(db, product_data, vendor.id)
        print(f"✅ Product saved with ID: {created_product.id}")
        
        # 🔧 MANUAL FIX: Generate presigned URLs manually
        print(f"🔗 Generating presigned URLs for response...")
        presigned_urls = []
        for key in created_product.image_urls:
            try:
                url = generate_presigned_url(key)
                presigned_urls.append(url)
                print(f"✅ Generated presigned URL for key: {key}")
            except Exception as url_error:
                print(f"❌ Failed to generate URL for key {key}: {url_error}")
                # Add a placeholder or skip this image
                continue
        
        # Create response with presigned URLs
        product_response = ProductOut(
            id=created_product.id,
            name=created_product.name,
            description=created_product.description,
            category=created_product.category,
            stock=created_product.stock,
            price=created_product.price,
            image_urls=presigned_urls,  # 🔧 FIXED: Return presigned URLs to frontend
            vendor_id=created_product.vendor_id,
            created_at=created_product.created_at,
            pricing_tiers=created_product.pricing_tiers
        )

        print(f"🎉 Product creation completed successfully!")
        print(f"📷 Returning {len(presigned_urls)} presigned URLs to frontend")
        
        return product_response

    except Exception as e:
        print(f"❌ Error creating product: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")
# ✅ Get all products for a vendor
@router.get("/", response_model=List[ProductOut])
def get_products(
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """Get all products for the current vendor with presigned URLs."""
    print(f"📋 Getting products for vendor {vendor.id}")
    
    products = crud_product.get_products_by_vendor(db, vendor_id=vendor.id, skip=skip, limit=limit)
    print(f"📋 Found {len(products)} products")
    
    # Convert S3 keys to presigned URLs for each product
    products_with_urls = []
    for product in products:
        print(f"🔗 Generating presigned URLs for product {product.id}")
        presigned_urls = get_presigned_urls_for_product(product.image_urls)
        
        product_response = ProductOut(
            id=product.id,
            name=product.name,
            description=product.description,
            category=product.category,
            stock=product.stock,
            price=product.price,
            image_urls=presigned_urls,  # Presigned URLs
            vendor_id=product.vendor_id,
            created_at=product.created_at,
            pricing_tiers=product.pricing_tiers
        )
        products_with_urls.append(product_response)
    
    print(f"✅ Returning {len(products_with_urls)} products with presigned URLs")
    return products_with_urls

# ✅ Get single product by ID
@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """Get a single product by ID with presigned URLs."""
    print(f"📄 Getting product {product_id} for vendor {vendor.id}")
    
    product = crud_product.get_product(db, product_id=product_id)
    
    if not product:
        print(f"❌ Product {product_id} not found")
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.vendor_id != vendor.id:
        print(f"❌ Vendor {vendor.id} not authorized for product {product_id}")
        raise HTTPException(status_code=403, detail="Not authorized to access this product")
    
    # Convert S3 keys to presigned URLs
    print(f"🔗 Generating presigned URLs for product {product_id}")
    presigned_urls = get_presigned_urls_for_product(product.image_urls)
    
    product_response = ProductOut(
        id=product.id,
        name=product.name,
        description=product.description,
        category=product.category,
        stock=product.stock,
        price=product.price,
        image_urls=presigned_urls,  # Presigned URLs
        vendor_id=product.vendor_id,
        created_at=product.created_at,
        pricing_tiers=product.pricing_tiers
    )
    
    print(f"✅ Returning product {product_id} with {len(presigned_urls)} presigned URLs")
    return product_response