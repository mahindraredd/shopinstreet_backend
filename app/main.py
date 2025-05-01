from fastapi.openapi.utils import get_openapi

from fastapi import FastAPI
from app.db.session import engine, Base
from app.api.routes_vendor import router as vendor_router
from app.api.routes_product import router as product_router
from app.api.routes_order import router as order_router
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI(
    title="vendor-product-api",
    description="basically it has all the details of the vendor and product",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 👈 Replace * with your frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# Register endpoints with descriptions
app.include_router(
    vendor_router, 
    prefix="/api/vendor", 
    tags=["Vendor"],
    
)
app.include_router(
    product_router, 
    prefix="/api/products", 
    tags=["Product"],
    
)

app.include_router(
    order_router, 
    prefix="/api/orders", 
    tags=["Order"],   
    
)



# 👇 Add custom OpenAPI with Bearer Auth
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Vendor Backend API",
        version="1.0.0",
        description="API for vendors to manage registration, login, and products.",
        routes=app.routes,
    )

    # Add Bearer auth globally
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
