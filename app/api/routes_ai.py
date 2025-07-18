# Create: app/api/routes_ai.py

import os
import time
import aiofiles
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.deps import get_db, get_current_vendor
from app.models.vendor import Vendor
from app.services.ai_product_service import AIProductService
from app.core.config import settings

router = APIRouter()

@router.post("/extract-product")
async def extract_product_info(
    file: UploadFile = File(...),
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Extract product information from image using AI."""
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    # Save temp file
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    temp_path = os.path.join(settings.UPLOAD_DIR, f"temp_{vendor.id}_{int(time.time())}.jpg")
    
    try:
        # Save uploaded file
        content = await file.read()
        async with aiofiles.open(temp_path, 'wb') as f:
            await f.write(content)
        
        # Extract with AI
        ai_service = AIProductService()
        result = await ai_service.extract_from_image(temp_path, vendor.id)
        
        return {
            "success": True,
            "message": "Product info extracted successfully",
            "data": result
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Extraction failed: {str(e)}"
        }
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

@router.get("/test")
def test_ai():
    """Test AI endpoint."""
    return {
        "message": "AI endpoint working",
        "openai_configured": bool(settings.OPENAI_API_KEY)
    }