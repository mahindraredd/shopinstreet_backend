import psycopg2
import psycopg2.extras
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_domain_tables():
    """
    Production database migration for domain system
    Creates all necessary tables with proper indexes
    """
    
    migration_sql = """
    -- Enable UUID extension for order numbers (optional)
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    
    -- Create domain_orders table
    CREATE TABLE IF NOT EXISTS domain_orders (
        id SERIAL PRIMARY KEY,
        vendor_id INTEGER NOT NULL REFERENCES vendor(id) ON DELETE CASCADE,
        order_number VARCHAR(50) UNIQUE NOT NULL,
        
        -- Domain details
        domain_name VARCHAR(255) NOT NULL,
        domain_type VARCHAR(20) NOT NULL CHECK (domain_type IN ('custom', 'purchased', 'subdomain')),
        template_id INTEGER NOT NULL,
        
        -- Pricing in INR
        domain_price_inr DECIMAL(10,2) NOT NULL,
        hosting_price_inr DECIMAL(10,2) DEFAULT 0.0,
        ssl_price_inr DECIMAL(10,2) DEFAULT 0.0,
        total_amount_inr DECIMAL(10,2) NOT NULL,
        
        -- Payment details
        payment_method VARCHAR(50),
        payment_id VARCHAR(100),
        payment_status VARCHAR(20) DEFAULT 'pending' CHECK (payment_status IN ('pending', 'processing', 'completed', 'failed', 'refunded')),
        razorpay_order_id VARCHAR(100),
        razorpay_payment_id VARCHAR(100),
        
        -- Order status tracking
        order_status VARCHAR(30) DEFAULT 'pending_purchase' CHECK (order_status IN ('available', 'pending_purchase', 'purchased', 'dns_configuring', 'hosting_setup', 'active', 'expired', 'failed', 'verification_pending')),
        completion_percentage INTEGER DEFAULT 0,
        current_step VARCHAR(100) DEFAULT 'payment_pending',
        
        -- Registrar details
        selected_registrar VARCHAR(20) CHECK (selected_registrar IN ('godaddy', 'namecheap')),
        domain_registration_id VARCHAR(100),
        registrar_order_id VARCHAR(100),
        expiry_date TIMESTAMP WITH TIME ZONE,
        
        -- Technical setup status
        dns_configured BOOLEAN DEFAULT FALSE,
        ssl_enabled BOOLEAN DEFAULT FALSE,
        hosting_active BOOLEAN DEFAULT FALSE,
        nameservers_updated BOOLEAN DEFAULT FALSE,
        
        -- Error handling
        error_message TEXT,
        retry_count INTEGER DEFAULT 0,
        max_retries INTEGER DEFAULT 3,
        
        -- Contact info (JSON)
        contact_info JSONB,
        
        -- Timestamps
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP WITH TIME ZONE,
        payment_confirmed_at TIMESTAMP WITH TIME ZONE
    );
    
    -- Update existing vendor_domains table or create if not exists
    CREATE TABLE IF NOT EXISTS vendor_domains (
        id SERIAL PRIMARY KEY,
        vendor_id INTEGER NOT NULL REFERENCES vendor(id) ON DELETE CASCADE,
        domain_name VARCHAR(255) UNIQUE NOT NULL,
        domain_type VARCHAR(20) NOT NULL CHECK (domain_type IN ('custom', 'purchased', 'subdomain')),
        status VARCHAR(30) DEFAULT 'active' CHECK (status IN ('available', 'pending_purchase', 'purchased', 'dns_configuring', 'hosting_setup', 'active', 'expired', 'failed', 'verification_pending')),
        
        -- Add new columns if they don't exist
        purchase_price_inr DECIMAL(10,2),
        renewal_price_inr DECIMAL(10,2),
        registrar VARCHAR(20) CHECK (registrar IN ('godaddy', 'namecheap')),
        registration_date TIMESTAMP WITH TIME ZONE,
        expiry_date TIMESTAMP WITH TIME ZONE,
        ssl_enabled BOOLEAN DEFAULT FALSE,
        dns_configured BOOLEAN DEFAULT FALSE,
        hosting_active BOOLEAN DEFAULT FALSE,
        template_id INTEGER,
        hosting_server VARCHAR(100),
        domain_order_id INTEGER REFERENCES domain_orders(id),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Add columns to existing vendor_domains if they don't exist
    DO $$ 
    BEGIN 
        -- Check and add missing columns
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vendor_domains' AND column_name='purchase_price_inr') THEN
            ALTER TABLE vendor_domains ADD COLUMN purchase_price_inr DECIMAL(10,2);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vendor_domains' AND column_name='renewal_price_inr') THEN
            ALTER TABLE vendor_domains ADD COLUMN renewal_price_inr DECIMAL(10,2);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vendor_domains' AND column_name='registrar') THEN
            ALTER TABLE vendor_domains ADD COLUMN registrar VARCHAR(20) CHECK (registrar IN ('godaddy', 'namecheap'));
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vendor_domains' AND column_name='hosting_server') THEN
            ALTER TABLE vendor_domains ADD COLUMN hosting_server VARCHAR(100);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='vendor_domains' AND column_name='domain_order_id') THEN
            ALTER TABLE vendor_domains ADD COLUMN domain_order_id INTEGER REFERENCES domain_orders(id);
        END IF;
    END $$;
    
    -- Update domain_suggestions table or create if not exists
    CREATE TABLE IF NOT EXISTS domain_suggestions (
        id SERIAL PRIMARY KEY,
        vendor_id INTEGER NOT NULL REFERENCES vendor(id) ON DELETE CASCADE,
        business_name VARCHAR(255) NOT NULL,
        suggested_domain VARCHAR(255) NOT NULL,
        tld VARCHAR(10) NOT NULL,
        
        -- Indian market pricing
        registration_price_inr DECIMAL(10,2) NOT NULL,
        renewal_price_inr DECIMAL(10,2) NOT NULL,
        
        -- Availability and scoring
        is_available BOOLEAN DEFAULT TRUE,
        is_premium BOOLEAN DEFAULT FALSE,
        recommendation_score DECIMAL(3,2) DEFAULT 0.0,
        is_popular_tld BOOLEAN DEFAULT FALSE,
        
        -- Registrar pricing comparison
        godaddy_price_inr DECIMAL(10,2),
        namecheap_price_inr DECIMAL(10,2),
        best_registrar VARCHAR(20) CHECK (best_registrar IN ('godaddy', 'namecheap')),
        
        -- Cache management
        availability_checked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        cache_expires_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create performance indexes
    CREATE INDEX IF NOT EXISTS idx_domain_orders_vendor_id ON domain_orders(vendor_id);
    CREATE INDEX IF NOT EXISTS idx_domain_orders_status ON domain_orders(order_status);
    CREATE INDEX IF NOT EXISTS idx_domain_orders_payment_status ON domain_orders(payment_status);
    CREATE INDEX IF NOT EXISTS idx_domain_orders_created_at ON domain_orders(created_at);
    CREATE INDEX IF NOT EXISTS idx_domain_orders_domain_name ON domain_orders(domain_name);
    CREATE INDEX IF NOT EXISTS idx_domain_orders_payment_id ON domain_orders(payment_id);
    
    CREATE INDEX IF NOT EXISTS idx_vendor_domains_vendor_id ON vendor_domains(vendor_id);
    CREATE INDEX IF NOT EXISTS idx_vendor_domains_domain_name ON vendor_domains(domain_name);
    CREATE INDEX IF NOT EXISTS idx_vendor_domains_status ON vendor_domains(status);
    CREATE INDEX IF NOT EXISTS idx_vendor_domains_expiry_date ON vendor_domains(expiry_date);
    
    CREATE INDEX IF NOT EXISTS idx_domain_suggestions_vendor_id ON domain_suggestions(vendor_id);
    CREATE INDEX IF NOT EXISTS idx_domain_suggestions_business_name ON domain_suggestions(business_name);
    CREATE INDEX IF NOT EXISTS idx_domain_suggestions_domain ON domain_suggestions(suggested_domain);
    CREATE INDEX IF NOT EXISTS idx_domain_suggestions_tld ON domain_suggestions(tld);
    CREATE INDEX IF NOT EXISTS idx_domain_suggestions_available ON domain_suggestions(is_available);
    
    -- Create updated_at trigger function
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    
    -- Create triggers for updated_at
    DROP TRIGGER IF EXISTS update_domain_orders_updated_at ON domain_orders;
    CREATE TRIGGER update_domain_orders_updated_at 
        BEFORE UPDATE ON domain_orders 
        FOR EACH ROW 
        EXECUTE FUNCTION update_updated_at_column();
        
    DROP TRIGGER IF EXISTS update_vendor_domains_updated_at ON vendor_domains;
    CREATE TRIGGER update_vendor_domains_updated_at 
        BEFORE UPDATE ON vendor_domains 
        FOR EACH ROW 
        EXECUTE FUNCTION update_updated_at_column();
    """
    
    try:
        # Connect to database
        logger.info("🔌 Connecting to database...")
        conn = psycopg2.connect(settings.DATABASE_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Execute migration
        logger.info("📊 Creating domain tables...")
        cur.execute(migration_sql)
        conn.commit()
        
        # Verify tables were created
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('domain_orders', 'vendor_domains', 'domain_suggestions')
            ORDER BY table_name;
        """)
        
        tables = cur.fetchall()
        logger.info(f"✅ Domain tables created successfully: {[t['table_name'] for t in tables]}")
        
        # Check indexes
        cur.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename IN ('domain_orders', 'vendor_domains', 'domain_suggestions')
            AND indexname LIKE 'idx_%'
            ORDER BY indexname;
        """)
        
        indexes = cur.fetchall()
        logger.info(f"✅ Performance indexes created: {len(indexes)} indexes")
        
        logger.info("🎉 STEP 1 COMPLETED: Database models and tables are ready!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_domain_tables()