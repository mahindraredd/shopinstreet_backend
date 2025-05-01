import io
import base64
import uuid
from PIL import Image, ImageEnhance, ImageOps
import boto3
from rembg import remove
from app.core.config import Settings
from app.utils.s3 import upload_to_s3

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

async def process_and_upload_images(files, vendor_id: int, product_id: int):
    uploaded_urls = []

    if len(files) > 6:
        raise ValueError("You can upload a maximum of 6 images.")

    for idx, file in enumerate(files):
        raw_bytes = await file.read()
        cleaned_bytes = clean_product_image(raw_bytes)
        url = upload_to_s3(cleaned_bytes, vendor_id, product_id, idx+1)
        uploaded_urls.append(url)

    return uploaded_urls

async def process_and_upload_images1(content: bytes, vendor_id: int) -> str:
    # 1. Clean the image
    cleaned_buf = clean_product_image(content)
    
    # 2. Upload to S3
    filename = f"vendor_{vendor_id}/temp/{uuid.uuid4()}.jpg"
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name="us-east-2"
       
    )

    s3.put_object(
        Bucket="shopinstreet-vendor-product-images",
        Key=filename,
        Body=cleaned_buf,
        ContentType="image/jpeg",
    )

    # 3. Return public URL
    url = f"https://shopinstreet-vendor-product-images.s3.us-east-2.amazonaws.com/{filename}"
    return filename

from urllib.parse import urlparse, parse_qs
def extract_key_from_url(url: str) -> str:
    parsed_url = urlparse(url)
    bucket_name = parsed_url.netloc.split('.')[0]
    key = parsed_url.path.lstrip('/')
    return key

import boto3
from botocore.exceptions import ClientError
import os

def generate_presigned_url(object_key: str, expiration: int = 3600) -> str:
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name="us-east-2"
       
    )
    aws_bucket_name = "shopinstreet-vendor-product-images"
    print(f"aws_bucket_name:",aws_bucket_name)
    print(f"object_key:",object_key)
    print(f"expiration:",expiration)
    try:
        response = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': aws_bucket_name, 'Key': object_key},
            ExpiresIn=expiration
        )
        return response
    except ClientError as e:
        raise Exception(f"Failed to generate presigned URL: {e}")

