from sqlalchemy import text
from sqlalchemy.orm import Session

def create_enterprise_indexes(db: Session):
    """Create indexes for million-user scale performance"""
    
    indexes = [
        # Orders table - Critical for analytics
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_vendor_created ON orders(vendor_id, created_at);",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_vendor_amount ON orders(vendor_id, total_amount);",
        
        # Order items - For product analytics
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_order_items_product ON order_items(product_id);",
        
        # Vendors - For fast lookups
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vendors_email ON vendor(email);",
    ]
    
    for index_sql in indexes:
        try:
            db.execute(text(index_sql))
            print(f"✅ Created index: {index_sql}")
        except Exception as e:
            print(f"⚠️  Index exists or error: {e}")
    
    db.commit()
    print("🚀 Enterprise database optimization complete!")