# Create: app/services/ai_product_service.py

import json
import base64
import asyncio
from typing import Dict, Any
from PIL import Image
import io
from openai import OpenAI
from app.core.config import settings
import re

class AIProductService:
    """Simple AI service for product extraction."""
    
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def extract_from_image(self, image_path: str, vendor_id: int) -> Dict[str, Any]:
        """Extract product info from image."""
        try:
            # Process image
            image_base64 = self._process_image(image_path)
            
            # Get AI analysis
            result = await self._analyze_with_ai(image_base64)
            
            # Format for your product form
            return self._format_result(result, vendor_id)
            
        except Exception as e:
            raise Exception(f"AI extraction failed: {str(e)}")
    
    def _process_image(self, image_path: str) -> str:
        """Convert image to base64."""
        with Image.open(image_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize for AI
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=95)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
    


    async def _analyze_with_ai(self, image_base64: str) -> Dict[str, Any]:
        prompt = """
    Analyze this product image and extract information for e-commerce listing and you are the best Product Analyst.

Analyze this product image and extract product details for an e-commerce listing.

Return ONLY valid JSON in this exact format, with the description as bullet points:

{
    "name": "Specific product name",
    "description":  {
    "summary": "A rich, engaging paragraph introducing the product with key benefits and purpose.",
    "features": [
      "Feature or benefit #1 with clear details",
      "Feature or benefit #2 with specs or advantages",
      "Feature or benefit #3 explaining usage or quality",
      "Additional points that add value"
    ]
  },
    "category": "Electronics|Clothing|Home & Kitchen|Beauty|Toys & Games|Books|Food & Grocery|Health|Other",
    "specifications": {
        "color": "primary color",
        "material": "material if visible",
        "brand": "brand if visible"
    },
    "tags": ["tag1", "tag2", "tag3"],
    "confidence": 0.85
}

Requirements:
- Be accurate and specific
-"features" should list 5-8 detailed bullet points, including specs and benefits
- Use clear, concise bullet points for the description (3-5 points)
- Choose the category only from the given list
- Include 3-5 relevant tags that describe the product well
- Estimate confidence as a decimal between 0.0 and 1.0
- Do NOT include any text outside the JSON

    """

        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model=settings.AI_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        # Using image_url this way might not be supported — 
                        # check API docs or use file upload if possible
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                        }
                    ]
                }],
                max_tokens=1000
            )
        )

        content = response.choices[0].message.content
        print("Raw AI content:", content)

        # Attempt to extract JSON if surrounded by code block or text
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if not json_match:
                json_match = re.search(r'```(.*?)```', content, re.DOTALL)
            if not json_match:
                json_match = re.search(r'(\{.*\})', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError as e:
                    raise Exception(f"JSON extraction failed: {str(e)}")
            raise Exception("No valid JSON found in AI response")
    
    def _format_result(self, ai_result: Dict[str, Any], vendor_id: int) -> Dict[str, Any]:
        """Format result for your product form."""
        return {
            "name": ai_result.get("name", ""),
            "description": ai_result.get("description", ""),
            "category": ai_result.get("category", ""),
            "stock": int(ai_result.get("stock", 100)),
            "price": float(ai_result.get("price", 0)),
            "pricing_tiers": ai_result.get("pricing_tiers", []),
            "vendor_id": vendor_id,
            "ai_extracted": True
        }