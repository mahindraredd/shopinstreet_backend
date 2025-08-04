import json
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.crud import product as crud_product
from app.db.deps import get_db, get_current_vendor
from app.models.vendor import Vendor
from app.services.image_service import (
    generate_presigned_url,
    process_and_upload_with_type,
    get_presigned_urls_for_product,
    extract_s3_key_from_presigned_url,
    process_and_upload_images1
)

router = APIRouter()

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
    pricing_tiers: str = Form(...),
    processing_type: str = Form(default="enhanced"),
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor),
):
    try:
        print(f"🏪 Creating product for vendor {vendor.id}: {name}")
        print(f"🔧 Processing type received: '{processing_type}'")  # Debug log
        
        pricing_tiers_data = json.loads(pricing_tiers)
        if not isinstance(pricing_tiers_data, list):
            raise ValueError("pricing_tiers must be a list of objects")

        # Validate and log processing type
        if processing_type not in ["raw", "enhanced"]:
            print(f"⚠️ Invalid processing type '{processing_type}', defaulting to 'enhanced'")
            processing_type = "enhanced"
        
        print(f"🔧 Final processing type: '{processing_type}'")  # Debug log

        image_keys = []
        for i, img in enumerate(images):
            if img.filename and img.filename != 'dummy.txt' and img.size > 0:
                print(f"📸 Processing image {i+1}: {img.filename} with type '{processing_type}'")  # Debug log
                
                content = await img.read()
                
                # Add detailed debug logging
                print(f"🔧 Calling process_and_upload_with_type with:")
                print(f"   - vendor_id: {vendor.id}")
                print(f"   - processing_type: '{processing_type}'")
                print(f"   - original_filename: '{img.filename}'")
                
                s3_key = await process_and_upload_with_type(
                    content=content,
                    vendor_id=vendor.id,
                    processing_type=processing_type,
                    original_filename=img.filename
                )
                
                print(f"✅ Received S3 key: {s3_key}")  # Debug log
                
                # Check if the S3 key indicates the right processing type
                if processing_type == "raw" and "/raw/" not in s3_key:
                    print(f"❌ ERROR: Expected /raw/ in S3 key for raw processing, got: {s3_key}")
                elif processing_type == "enhanced" and "/enhanced/" not in s3_key:
                    print(f"❌ ERROR: Expected /enhanced/ in S3 key for enhanced processing, got: {s3_key}")
                
                if not isinstance(s3_key, str):
                    raise ValueError("Image processing failed. Expected S3 key string.")
                image_keys.append(s3_key)

        # ✅ FIXED: Remove vendor_id from ProductCreate (it's not in the schema)
        product_data = ProductCreate(
            name=name,
            description=description,
            category=category,
            stock=stock,
            price=price,
            pricing_tiers=pricing_tiers_data,
            image_urls=image_keys,
            # vendor_id=vendor.id  # ❌ REMOVED - not in schema
        )

        product = crud_product.create_product(db=db, vendor_id=vendor.id, data=product_data)
        presigned_urls = get_presigned_urls_for_product(image_keys)

        product_dict = {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "category": product.category,
            "stock": product.stock,
            "price": product.price,
            "pricing_tiers": product.pricing_tiers,
            "image_urls": presigned_urls,
            "vendor_id": product.vendor_id,
            "created_at": product.created_at.isoformat(),
        }

        print(f"🎉 Product created successfully with processing type: {processing_type}")
        return ProductOut(**product_dict)

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid pricing_tiers JSON format")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error creating product: {e}")
        import traceback
        traceback.print_exc()  # Print full error traceback
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
@router.get("/mine", response_model=List[ProductOut])
def list_my_products(
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    skip = (page - 1) * size
    products = crud_product.get_products_by_vendor(db, vendor.id, skip=skip, limit=size)
    products_with_urls = []
    for product in products:
        try:
            presigned_urls = [generate_presigned_url(key) for key in product.image_urls] if product.image_urls else []
            product_response = ProductOut(
                id=product.id,
                name=product.name,
                description=product.description,
                category=product.category,
                stock=product.stock,
                price=product.price,
                image_urls=presigned_urls,
                vendor_id=product.vendor_id,
                created_at=product.created_at,
                pricing_tiers=product.pricing_tiers or []
            )
            products_with_urls.append(product_response)
        except Exception:
            continue
    return products_with_urls

@router.get("/mine-simple", response_model=List[ProductOut])
def list_my_products_simple(
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    skip = (page - 1) * size
    products = crud_product.get_products_by_vendor(db, vendor.id, skip=skip, limit=size)
    products_with_urls = []
    for product in products:
        try:
            presigned_urls = get_presigned_urls_for_product(product.image_urls)
            product_response = ProductOut(
                id=product.id,
                name=product.name,
                description=product.description,
                category=product.category,
                stock=product.stock,
                price=product.price,
                image_urls=presigned_urls,
                vendor_id=product.vendor_id,
                created_at=product.created_at,
                pricing_tiers=product.pricing_tiers or []
            )
            products_with_urls.append(product_response)
        except Exception:
            continue
    return products_with_urls

@router.get("/all", response_model=List[ProductOut])
def list_all_products(db: Session = Depends(get_db)):
    return crud_product.get_all_products(db)

@router.get("/{product_id}", response_model=ProductOut)
def get_product_by_id_route(
    product_id: int,
    db: Session = Depends(get_db)
):
    product = crud_product.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.image_urls = [generate_presigned_url(obj_key) for obj_key in product.image_urls]
    return product

@router.post("/{product_id}/images", response_model=ProductOut)
async def update_product_images(
    product_id: int,
    images: List[UploadFile] = File(...),
    existing_images: Optional[str] = Form(None),
    processing_type: str = Form(default="enhanced"),  # 👈 NEW: Add processing type
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    try:
        existing_product = crud_product.get_product_by_id(db, product_id)
        if not existing_product or existing_product.vendor_id != vendor.id:
            raise HTTPException(
                status_code=404,
                detail="Product not found or you don't have permission to update it"
            )

        print(f"🔄 Updating images for product {product_id}")
        print(f"🔧 Processing type: {processing_type}")  # 👈 NEW: Log processing type

        # Validate processing type
        if processing_type not in ["raw", "enhanced"]:
            print(f"⚠️ Invalid processing type '{processing_type}', defaulting to 'enhanced'")
            processing_type = "enhanced"

        existing_image_keys = []
        if existing_images:
            try:
                existing_presigned_urls = json.loads(existing_images)
                for url in existing_presigned_urls:
                    try:
                        s3_key = extract_s3_key_from_presigned_url(url)
                        existing_image_keys.append(s3_key)
                    except ValueError:
                        continue
            except json.JSONDecodeError:
                pass

        new_image_keys = []
        for img in images:
            if img.filename and img.filename != 'dummy.txt' and img.size > 0:
                content = await img.read()
                if len(content) == 0:
                    continue
                try:
                    # 👈 FIXED: Use process_and_upload_with_type instead of process_and_upload_images1
                    s3_key = await process_and_upload_with_type(
                        content=content,
                        vendor_id=vendor.id,
                        processing_type=processing_type,
                        original_filename=img.filename
                    )
                    if not isinstance(s3_key, str):
                        raise ValueError("Image processing failed. Expected S3 key string.")
                    new_image_keys.append(s3_key)
                    print(f"✅ Uploaded new image with key: {s3_key}")
                except Exception as e:
                    print(f"❌ Failed to process {img.filename}: {str(e)}")
                    continue

        all_image_keys = existing_image_keys + new_image_keys

        if len(all_image_keys) > 6:
            raise HTTPException(
                status_code=400,
                detail=f"Too many images. Maximum 6 allowed, got {len(all_image_keys)}"
            )

        if len(all_image_keys) == 0:
            raise HTTPException(
                status_code=400,
                detail="At least one image is required"
            )

        updated_product = crud_product.update_product_images(db, product_id, all_image_keys)
        if not updated_product:
            raise HTTPException(status_code=404, detail="Failed to update product images")

        if updated_product.image_urls:
            updated_product.image_urls = [
                generate_presigned_url(key) for key in updated_product.image_urls
            ]
        
        print(f"🎉 Successfully updated product {product_id} with processing type: {processing_type}")
        return updated_product

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update images: {str(e)}")
@router.patch("/{product_id}/details", response_model=ProductOut)
async def update_product_details(
    product_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    stock: Optional[int] = Form(None),
    price: Optional[float] = Form(None),
    pricing_tiers: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    try:
        existing_product = crud_product.get_product_by_id(db, product_id)
        if not existing_product or existing_product.vendor_id != vendor.id:
            raise HTTPException(status_code=404, detail="Product not found or unauthorized")

        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if category is not None:
            update_data["category"] = category
        if stock is not None:
            update_data["stock"] = stock
        if price is not None:
            update_data["price"] = price

        if pricing_tiers is not None:
            try:
                parsed_pricing_tiers = json.loads(pricing_tiers)
                if not isinstance(parsed_pricing_tiers, list):
                    raise ValueError("pricing_tiers must be a list of objects")
                update_data["pricing_tiers"] = parsed_pricing_tiers
                if parsed_pricing_tiers and not price:
                    update_data["price"] = parsed_pricing_tiers[0].get("price")
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON format for pricing_tiers"
                )

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update"
            )

        product_update = ProductUpdate(**update_data)
        updated_product = crud_product.update_product(db, product_id, vendor.id, product_update)
        if not updated_product:
            raise HTTPException(
                status_code=404,
                detail="Product update failed"
            )

        if updated_product.image_urls:
            updated_product.image_urls = [
                generate_presigned_url(key) for key in updated_product.image_urls
            ]

        return updated_product

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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
    return crud_product.search_products_by_vendor(db, vendor.id, query)