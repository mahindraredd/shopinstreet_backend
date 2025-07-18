# Updated app/services/image_service.py

import io
import base64
import uuid
import os
from PIL import Image, ImageEnhance, ImageOps
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from rembg import remove
from app.core.config import settings
from app.utils.s3 import upload_to_s3
from urllib.parse import urlparse, parse_qs

load_dotenv()

def clean_product_image(image_bytes: bytes) -> bytes:
    """Clean and enhance product image"""
    input_image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    no_bg = remove(input_image)
    white_bg = Image.new("RGBA", no_bg.size, (255, 255, 255, 255))
    white_bg.paste(no_bg, (0, 0), no_bg)
    final_img = white_bg.convert("RGB")
    final_img = ImageEnhance.Contrast(final_img).enhance(1.1)
    final_img = ImageEnhance.Sharpness(final_img).enhance(2.0)
    final_img = ImageOps.pad(final_img, (1024, 1024), color="white")
    
    buf = io.BytesIO()
    final_img.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    return buf.getvalue()

def generate_presigned_url(object_key: str, expiration: int = 3600) -> str:
    """Generate presigned URL for S3 object"""
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name="us-east-2"
    )
    aws_bucket_name = "shopinstreet-vendor-product-images"
    
    print(f"Generating presigned URL for bucket: {aws_bucket_name}, key: {object_key}")
    
    try:
        response = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': aws_bucket_name, 'Key': object_key},
            ExpiresIn=expiration
        )
        print(f" Presigned URL generated successfully")
        return response
    except ClientError as e:
        print(f" Failed to generate presigned URL: {e}")
        raise Exception(f"Failed to generate presigned URL: {e}")

async def process_and_upload_images1(content: bytes, vendor_id: int) -> str:
    """
    Process image and upload to S3.
    Returns the S3 key (not the full URL) - presigned URLs generated separately
    """
    # 1. Clean the image
    cleaned_buf = clean_product_image(content)
    
    # 2. Generate S3 key
    filename = f"vendor_{vendor_id}/products/{uuid.uuid4()}.jpg"
    
    # 3. Upload to S3
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name="us-east-2"
    )

    try:
        s3.put_object(
            Bucket="shopinstreet-vendor-product-images",
            Key=filename,
            Body=cleaned_buf,
            ContentType="image/jpeg",
            CacheControl="private, max-age=3600"  # Private cache
        )
        print(f" Image uploaded to S3 with key: {filename}")
        
        # 4. Return the S3 key (not full URL)
        return filename
        
    except Exception as e:
        print(f" Failed to upload image to S3: {e}")
        raise Exception(f"Failed to upload image: {e}")

async def process_and_upload_images(files, vendor_id: int, product_id: int):
    """Process and upload multiple images, return S3 keys"""
    uploaded_keys = []

    if len(files) > 6:
        raise ValueError("You can upload a maximum of 6 images.")

    for idx, file in enumerate(files):
        raw_bytes = await file.read()
        cleaned_bytes = clean_product_image(raw_bytes)
        
        # Generate S3 key
        filename = f"vendor_{vendor_id}/products/product_{product_id}/image_{idx+1}_{uuid.uuid4()}.jpg"
        
        # Upload to S3
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name="us-east-2"
        )
        
        try:
            s3.put_object(
                Bucket="shopinstreet-vendor-product-images",
                Key=filename,
                Body=cleaned_bytes,
                ContentType="image/jpeg",
                CacheControl="private, max-age=3600"
            )
            uploaded_keys.append(filename)  # Return S3 key, not URL
            print(f" Image {idx+1} uploaded with key: {filename}")
        except Exception as e:
            print(f" Failed to upload image {idx+1}: {e}")
            raise Exception(f"Failed to upload image {idx+1}: {e}")

    return uploaded_keys

def get_presigned_urls_for_product(image_keys: list, expiration: int = 3600) -> list:
    """Convert list of S3 keys to presigned URLs"""
    presigned_urls = []
    
    print(f"Converting {len(image_keys)} S3 keys to presigned URLs")
    
    for i, key in enumerate(image_keys):
        try:
            # Skip empty or invalid keys
            if not key or not isinstance(key, str):
                print(f"  Skipping invalid key at index {i}: {key}")
                continue
                
            presigned_url = generate_presigned_url(key, expiration)
            presigned_urls.append(presigned_url)
            print(f" Generated presigned URL for key {i+1}/{len(image_keys)}")
            
        except Exception as e:
            print(f" Failed to generate presigned URL for key '{key}': {e}")
            # Skip failed URLs rather than breaking the whole response
            continue
    
    print(f"✅ Successfully generated {len(presigned_urls)} presigned URLs")
    return presigned_urls

def extract_key_from_url(url: str) -> str:
    """Extract S3 key from full S3 URL"""
    parsed_url = urlparse(url)
    bucket_name = parsed_url.netloc.split('.')[0]
    key = parsed_url.path.lstrip('/')
    return key

def refresh_presigned_url(s3_key: str, expiration: int = 3600) -> str:
    """Refresh a single presigned URL"""
    return generate_presigned_url(s3_key, expiration)