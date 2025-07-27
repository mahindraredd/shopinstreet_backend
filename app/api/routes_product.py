
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
    get_presigned_urls_for_product,
    extract_s3_key_from_presigned_url,  
    generate_presigned_url_safe  
)
router = APIRouter()

# 🔹 Test route
@router.get("/test")
def test():
    return {"message": "Product route is working"}

# app/api/routes_product.py - Replace your BROKEN create product endpoint

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
    FIXED: Now returns presigned URLs instead of S3 keys
    """
    try:
        print(f"🏪 Creating product for vendor {vendor.id}: {name}")
        
        # Parse pricing_tiers JSON
        pricing_tiers_data = json.loads(pricing_tiers)
        print(f"📊 Pricing tiers: {pricing_tiers_data}")

        # Validate pricing_tiers format
        if not isinstance(pricing_tiers_data, list):
            raise ValueError("pricing_tiers must be a list of objects")

        # Upload images to S3 and get S3 keys
        print(f"📸 Processing {len(images)} images...")
        image_keys = []  # These will be S3 keys, not URLs
        
        for i, img in enumerate(images):
            print(f"📸 Processing image {i+1}/{len(images)}: {img.filename}")
            content = await img.read()
            s3_key = await process_and_upload_images1(content, vendor.id)
            if not isinstance(s3_key, str):
                raise ValueError(f"Image {i+1} processing failed. Expected S3 key string.")
            image_keys.append(s3_key)
            print(f"✅ Image {i+1} uploaded with key: {s3_key}")

        print(f"✅ All images uploaded. Keys: {image_keys}")

        # Create ProductCreate object with S3 keys (for database storage)
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
        created_product = crud_product.create_product(db=db, data=product_data, vendor_id=vendor.id)
        print(f"✅ Product saved with ID: {created_product.id}")
        
        # 🔧 CRITICAL FIX: Generate presigned URLs for the response
        print(f"🔗 Generating presigned URLs for response...")
        presigned_urls = []
        
        if created_product.image_urls:
            for key in created_product.image_urls:
                try:
                    if key and isinstance(key, str):
                        url = generate_presigned_url(key)
                        presigned_urls.append(url)
                        print(f"✅ Generated presigned URL for key: {key}")
                except Exception as e:
                    print(f"❌ Failed to generate URL for key {key}: {e}")
                    continue
        
        print(f"✅ Generated {len(presigned_urls)} presigned URLs")

        # 🔧 FIXED: Return ProductOut with presigned URLs
        product_response = ProductOut(
            id=created_product.id,
            vendor_id=created_product.vendor_id,
            name=created_product.name,
            description=created_product.description,
            category=created_product.category,
            stock=created_product.stock,
            price=created_product.price,
            pricing_tiers=created_product.pricing_tiers,
            image_urls=presigned_urls,  # 🔧 FIXED: Return presigned URLs, not S3 keys
            created_at=created_product.created_at,
        )

        print(f"🎉 Product creation completed successfully!")
        print(f"📷 Returning {len(presigned_urls)} presigned URLs to frontend")
        
        return product_response

    except json.JSONDecodeError:
        print(f"❌ Invalid JSON format for pricing_tiers")
        raise HTTPException(status_code=400, detail="Invalid JSON format for pricing_tiers")
    except Exception as e:
        print(f"❌ Error creating product: {e}")
        raise HTTPException(status_code=400, detail=str(e))
#  List current vendor's products
# app/api/routes_product.py - Fixed /mine endpoint

@router.get("/mine", response_model=List[ProductOut])
def list_my_products(
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """
    List paginated products belonging to the logged-in vendor.
    FIXED: Now properly returns ProductOut objects with presigned URLs
    """
    skip = (page - 1) * size
    products = crud_product.get_products_by_vendor(db, vendor.id, skip=skip, limit=size)

    print(f"📋 Found {len(products)} products for vendor {vendor.id}")
    
    # 🔧 FIXED: Create proper ProductOut responses instead of modifying SQLAlchemy objects
    products_with_urls = []
    for product in products:
        try:
            # Generate presigned URLs for this product
            print(f"🔗 Generating presigned URLs for product {product.id}")
            presigned_urls = []
            
            if product.image_urls:
                for key in product.image_urls:
                    try:
                        if key and isinstance(key, str):
                            url = generate_presigned_url(key)
                            presigned_urls.append(url)
                            print(f"✅ Generated URL for key: {key[:50]}...")
                    except Exception as e:
                        print(f"❌ Failed to generate URL for key {key}: {e}")
                        continue
            
            # Create proper ProductOut response
            product_response = ProductOut(
                id=product.id,
                name=product.name,
                description=product.description,
                category=product.category,
                stock=product.stock,
                price=product.price,
                image_urls=presigned_urls,  # 🔧 FIXED: Presigned URLs, not S3 keys
                vendor_id=product.vendor_id,
                created_at=product.created_at,
                pricing_tiers=product.pricing_tiers or []
            )
            
            products_with_urls.append(product_response)
            print(f"✅ Added product {product.id} with {len(presigned_urls)} presigned URLs")
            
        except Exception as e:
            print(f"❌ Error processing product {product.id}: {e}")
            # Skip this product rather than failing the whole request
            continue
    
    print(f"✅ Returning {len(products_with_urls)} products with presigned URLs")
    return products_with_urls


# Alternative simpler version using get_presigned_urls_for_product if you have it:
@router.get("/mine-simple", response_model=List[ProductOut])
def list_my_products_simple(
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """
    Alternative simpler version using get_presigned_urls_for_product
    """
    skip = (page - 1) * size
    products = crud_product.get_products_by_vendor(db, vendor.id, skip=skip, limit=size)

    print(f"📋 Found {len(products)} products for vendor {vendor.id}")
    
    # Create proper ProductOut responses
    products_with_urls = []
    for product in products:
        try:
            # Use the helper function if you have it
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
                pricing_tiers=product.pricing_tiers or []
            )
            
            products_with_urls.append(product_response)
            
        except Exception as e:
            print(f"❌ Error processing product {product.id}: {e}")
            continue
    
    print(f"✅ Returning {len(products_with_urls)} products with presigned URLs")
    return products_with_urls
#  Optional: List all products from all vendors
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


@router.post("/{product_id}/images", response_model=ProductOut)
async def update_product_images(
    product_id: int,
    images: List[UploadFile] = File(...),  # New images to upload
    existing_images: Optional[str] = Form(None),  # JSON string of existing images (presigned URLs)
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    """
    Update product images: keeps existing images + adds new uploads
    
    Args:
        product_id: ID of the product to update
        images: New image files to upload
        existing_images: JSON string of existing image URLs to keep (presigned URLs)
    """
    try:
        # Check if product exists and belongs to vendor
        existing_product = crud_product.get_product_by_id(db, product_id)
        if not existing_product or existing_product.vendor_id != vendor.id:
            raise HTTPException(
                status_code=404, 
                detail="Product not found or you don't have permission to update it"
            )
        
        print(f"🔄 Updating images for product {product_id}")
        print(f"📁 Received {len(images)} new files")
        print(f"📋 Existing images data: {existing_images}")
        
        # Parse and convert existing images from presigned URLs to S3 keys
        existing_image_keys = []
        if existing_images:
            try:
                existing_presigned_urls = json.loads(existing_images)
                print(f"📷 Processing {len(existing_presigned_urls)} existing images")
                
                for url in existing_presigned_urls:
                    try:
                        s3_key = extract_s3_key_from_presigned_url(url)
                        existing_image_keys.append(s3_key)
                        print(f"✅ Converted URL to key: {s3_key}")
                    except ValueError as e:
                        print(f"⚠️ Skipping invalid URL: {url} - {e}")
                        continue
                        
            except json.JSONDecodeError:
                print("⚠️ Failed to parse existing_images JSON, assuming no existing images")
        
        print(f"📷 Keeping {len(existing_image_keys)} existing images as S3 keys")
        
        # Process new image uploads (filter out dummy files)
        new_image_keys = []
        for i, img in enumerate(images):
            # Skip dummy files (empty files or specific dummy names)
            if (img.filename and 
                img.filename != 'dummy.txt' and 
                img.size > 0):
                
                print(f"📤 Processing new image {i+1}: {img.filename} ({img.size} bytes)")
                content = await img.read()
                
                # Skip if content is empty
                if len(content) == 0:
                    print(f"⚠️ Skipping empty file: {img.filename}")
                    continue
                    
                try:
                    s3_key = await process_and_upload_images1(content, vendor.id)
                    if not isinstance(s3_key, str):
                        raise ValueError("Image processing failed. Expected S3 key string.")
                    new_image_keys.append(s3_key)
                    print(f"✅ Successfully processed: {img.filename} -> {s3_key}")
                except Exception as e:
                    print(f"❌ Failed to process {img.filename}: {str(e)}")
                    continue
            else:
                print(f"⏭️ Skipping file: {img.filename} (dummy or empty)")
        
        print(f"✅ Successfully uploaded {len(new_image_keys)} new images")
        
        # Combine existing S3 keys + new S3 keys
        all_image_keys = existing_image_keys + new_image_keys
        print(f"📊 Total images after update: {len(all_image_keys)} S3 keys")
        print(f"🔑 Final S3 keys: {all_image_keys}")
        
        # Validate total image count
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
        
        # Update the product with all S3 keys (not URLs)
        updated_product = crud_product.update_product_images(db, product_id, all_image_keys)
        if not updated_product:
            raise HTTPException(status_code=404, detail="Failed to update product images")
        
        # Generate presigned URLs for the response (convert S3 keys back to URLs)
        if updated_product.image_urls:
            presigned_urls = [
                generate_presigned_url(key) for key in updated_product.image_urls
            ]
            updated_product.image_urls = presigned_urls
            print(f"🔗 Generated {len(presigned_urls)} presigned URLs for response")
        
        print(f"🎉 Successfully updated product {product_id} with {len(all_image_keys)} images")
        return updated_product
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f" Error updating product images: {str(e)}")
        print(f"Error details: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to update images: {str(e)}")    
@router.patch("/{product_id}/details", response_model=ProductOut)
async def update_product_details(
    product_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    stock: Optional[int] = Form(None),
    price: Optional[float] = Form(None),
    pricing_tiers: Optional[str] = Form(None),  # received as stringified JSON
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)    
):
    """
    Update product details excluding images.
    """
    try:
        existing_product = crud_product.get_product_by_id(db, product_id)
        if not existing_product or existing_product.vendor_id != vendor.id:
            raise HTTPException(status_code=404, detail="Product not found or unauthorized")
             
        # Prepare update data
        update_data = {}
        
        # Add fields that are provided
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
            
        # Handle pricing_tiers if provided
        if pricing_tiers is not None:
            try:
                parsed_pricing_tiers = json.loads(pricing_tiers)
                # Validate pricing_tiers format
                if not isinstance(parsed_pricing_tiers, list):
                    raise ValueError("pricing_tiers must be a list of objects")
                update_data["pricing_tiers"] = parsed_pricing_tiers
                
                # Update price from first tier if provided
                if parsed_pricing_tiers and not price:
                    update_data["price"] = parsed_pricing_tiers[0].get("price")
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid JSON format for pricing_tiers"
                )
        
        # If no fields to update, return early
        if not update_data:
            raise HTTPException(
                status_code=400, 
                detail="No fields provided for update"
            )
        
        # Create ProductUpdate schema from update_data
        product_update = ProductUpdate(**update_data)
        
        # Update the product
        updated_product = crud_product.update_product(db, product_id, vendor.id, product_update)
        if not updated_product:
            raise HTTPException(
                status_code=404, 
                detail="Product update failed"
            )
        
        # Generate presigned URLs for images
        if updated_product.image_urls:
            updated_product.image_urls = [
                generate_presigned_url(key) for key in updated_product.image_urls
            ]
        
        return updated_product
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error updating product details: {str(e)}")
        print(f"Error details: {error_details}")
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
    """
    🔍 Search products by name or category (only for the logged-in vendor).
    """
    return crud_product.search_products_by_vendor(db, vendor.id, query)




