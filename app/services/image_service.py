# app/services/image_service.py - Complete working version

import io
import uuid
import os
import boto3
from PIL import Image, ImageEnhance, ImageOps
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from rembg import remove
from typing import Optional, List
from urllib.parse import urlparse
from enum import Enum
import time

load_dotenv()

def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name="us-east-2"
    )

def clean_product_image(image_bytes: bytes) -> bytes:
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

def basic_image_optimization(image_bytes: bytes, max_size: tuple = (2048, 2048)) -> bytes:
    image = Image.open(io.BytesIO(image_bytes))
    if image.mode in ('RGBA', 'LA', 'P'):
        image = image.convert('RGB')
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85, optimize=True)
    buf.seek(0)
    return buf.getvalue()

def generate_presigned_url(object_key: str, expiration: int = 3600) -> str:
    s3 = get_s3_client()
    aws_bucket_name = "shopinstreet-vendor-product-images"
    try:
        response = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': aws_bucket_name, 'Key': object_key},
            ExpiresIn=expiration
        )
        return response
    except ClientError as e:
        raise Exception(f"Failed to generate presigned URL: {e}")

def extract_s3_key_from_presigned_url(presigned_url: str) -> str:
    try:
        if not presigned_url.startswith('http'):
            return presigned_url
        url_without_params = presigned_url.split('?')[0]
        parsed_url = urlparse(url_without_params)
        s3_key = parsed_url.path.lstrip('/')
        if not s3_key:
            raise ValueError(f"Empty S3 key extracted from URL: {presigned_url}")
        return s3_key
    except Exception as e:
        raise ValueError(f"Invalid image URL format: {presigned_url}")

def validate_s3_key_exists(s3_key: str) -> bool:
    try:
        s3 = get_s3_client()
        s3.head_object(Bucket="shopinstreet-vendor-product-images", Key=s3_key)
        return True
    except Exception:
        return False

def generate_presigned_url_safe(s3_key: str) -> str:
    try:
        return generate_presigned_url(s3_key)
    except Exception:
        return "https://via.placeholder.com/400x300?text=Error+Loading+Image"

def extract_key_from_url(url: str) -> str:
    parsed_url = urlparse(url.split('?')[0])
    key = parsed_url.path.lstrip('/')
    return key

def refresh_presigned_url(s3_key: str, expiration: int = 3600) -> str:
    return generate_presigned_url(s3_key, expiration)

class ImageProcessingType(str, Enum):
    RAW = "raw"
    ENHANCED = "enhanced"
    BASIC = "basic"

class ImageUploadResult:
    def __init__(self, s3_key: str, processing_type: ImageProcessingType, 
                 original_filename: str, file_size: int):
        self.s3_key = s3_key
        self.processing_type = processing_type
        self.original_filename = original_filename
        self.file_size = file_size
        self.upload_timestamp = int(time.time())

async def upload_raw_image(
    content: bytes, 
    vendor_id: int, 
    original_filename: str,
    product_id: Optional[int] = None
) -> ImageUploadResult:
    file_extension = original_filename.split('.')[-1] if '.' in original_filename else 'jpg'
    if product_id:
        s3_key = f"vendor_{vendor_id}/products/product_{product_id}/raw_{uuid.uuid4()}.{file_extension}"
    else:
        s3_key = f"vendor_{vendor_id}/raw/{uuid.uuid4()}.{file_extension}"
    s3 = get_s3_client()
    content_type = "image/jpeg"
    if file_extension.lower() == 'png':
        content_type = "image/png"
    elif file_extension.lower() == 'webp':
        content_type = "image/webp"
    s3.put_object(
        Bucket="shopinstreet-vendor-product-images",
        Key=s3_key,
        Body=content,
        ContentType=content_type,
        CacheControl="public, max-age=86400",
        Metadata={
            'vendor_id': str(vendor_id),
            'processing_type': 'raw',
            'original_filename': original_filename,
            'upload_type': 'direct'
        }
    )
    return ImageUploadResult(
        s3_key=s3_key,
        processing_type=ImageProcessingType.RAW,
        original_filename=original_filename,
        file_size=len(content)
    )

async def upload_with_processing(
    content: bytes, 
    vendor_id: int, 
    processing_type: ImageProcessingType,
    original_filename: str,
    product_id: Optional[int] = None
) -> ImageUploadResult:
    if processing_type == ImageProcessingType.RAW:
        return await upload_raw_image(content, vendor_id, original_filename, product_id)
    elif processing_type == ImageProcessingType.BASIC:
        processed_content = basic_image_optimization(content)
        processing_suffix = "basic"
    elif processing_type == ImageProcessingType.ENHANCED:
        processed_content = clean_product_image(content)
        processing_suffix = "enhanced"
    else:
        raise ValueError(f"Unknown processing type: {processing_type}")
    if product_id:
        s3_key = f"vendor_{vendor_id}/products/product_{product_id}/{processing_suffix}_{uuid.uuid4()}.jpg"
    else:
        s3_key = f"vendor_{vendor_id}/{processing_suffix}/{uuid.uuid4()}.jpg"
    s3 = get_s3_client()
    s3.put_object(
        Bucket="shopinstreet-vendor-product-images",
        Key=s3_key,
        Body=processed_content,
        ContentType="image/jpeg",
        CacheControl="public, max-age=86400",
        Metadata={
            'vendor_id': str(vendor_id),
            'processing_type': processing_type.value,
            'original_filename': original_filename
        }
    )
    return ImageUploadResult(
        s3_key=s3_key,
        processing_type=processing_type,
        original_filename=original_filename,
        file_size=len(processed_content)
    )

async def process_and_upload_images1(content: bytes, vendor_id: int) -> str:
    result = await upload_with_processing(
        content, vendor_id, ImageProcessingType.ENHANCED, "legacy_upload.jpg"
    )
    return result.s3_key

async def process_and_upload_images(files, vendor_id: int, product_id: int):
    uploaded_keys = []
    if len(files) > 6:
        raise ValueError("You can upload a maximum of 6 images.")
    for idx, file in enumerate(files):
        raw_bytes = await file.read()
        cleaned_bytes = clean_product_image(raw_bytes)
        filename = f"vendor_{vendor_id}/products/product_{product_id}/image_{idx+1}_{uuid.uuid4()}.jpg"
        s3 = get_s3_client()
        s3.put_object(
            Bucket="shopinstreet-vendor-product-images",
            Key=filename,
            Body=cleaned_bytes,
            ContentType="image/jpeg",
            CacheControl="private, max-age=3600"
        )
        uploaded_keys.append(filename)
    return uploaded_keys

def get_presigned_urls_for_product(image_keys: List[str], expiration: int = 3600) -> List[str]:
    presigned_urls = []
    for key in image_keys:
        try:
            if not key or not isinstance(key, str):
                continue
            presigned_url = generate_presigned_url(key, expiration)
            presigned_urls.append(presigned_url)
        except Exception:
            continue
    return presigned_urls

# Add this function to your app/services/image_service.py

async def process_and_upload_with_type(
    content: bytes, 
    vendor_id: int, 
    processing_type: str = "enhanced",
    original_filename: str = "image.jpg"
) -> str:
    """
    Upload image with specified processing type.
    
    Args:
        content: Image bytes
        vendor_id: Vendor ID  
        processing_type: "raw", "basic", "enhanced" (default is "enhanced" for backward compatibility)
        original_filename: Original filename for metadata
    
    Returns:
        S3 key string
    """
    
    # Convert string to enum
    if processing_type == "raw":
        proc_type = ImageProcessingType.RAW
    elif processing_type == "basic":
        proc_type = ImageProcessingType.BASIC
    elif processing_type == "enhanced":
        proc_type = ImageProcessingType.ENHANCED
    else:
        # Default to enhanced for backward compatibility
        proc_type = ImageProcessingType.ENHANCED
    
    # Use the existing upload_with_processing function
    result = await upload_with_processing(
        content=content,
        vendor_id=vendor_id,
        processing_type=proc_type,
        original_filename=original_filename
    )
    
    return result.s3_key