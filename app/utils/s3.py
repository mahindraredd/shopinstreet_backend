import os
import boto3
import uuid
from botocore.exceptions import NoCredentialsError


AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = "us-east-2"  # Example: us-east-1
AWS_BUCKET_NAME = "shopinstreet-vendor-product-images"

def upload_to_s3(file_bytes: bytes, vendor_id: int, product_id: int, file_index: int) -> str:
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )

        filename = f"vendor_{vendor_id}/product_{product_id}/image_{file_index}.jpg"

        s3.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=filename,
            Body=file_bytes,
            ContentType="image/jpeg"
        )

        url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{filename}"
        return url

    except NoCredentialsError:
        raise Exception("AWS credentials not available")
    except Exception as e:
        raise Exception(f"Failed to upload to S3: {str(e)}")
