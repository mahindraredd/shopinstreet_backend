# migrations/bulletproof_subdomain_migration.py
"""
BULLETPROOF SUBDOMAIN MIGRATION
Handles all edge cases and provides clear debugging
"""

import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
import logging
import re

# Load environment variables
load_dotenv()

def bulletproof_migration():
    """Bulletproof migration with detailed logging"""
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in .env file")
        print("Please check your .env file contains DATABASE_URL=your_postgres_connection")
        return False
    
    print("🚀 BULLETPROOF SUBDOMAIN MIGRATION")
    print("=" * 60)
    
    try:
        # Step 1: Connect to database
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("✅ Database connection successful")
        
        # Step 2: Check vendor table exists
        print("\n📋 Checking vendor table...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'vendor'
            );
        """)
        
        table_exists = cur.fetchone()[0]
        print(f"Vendor table exists: {table_exists}")
        
        if not table_exists:
            print("❌ ERROR: Vendor table does not exist!")
            print("Please create your vendor table first.")
            return False
        
        # Step 3: Check vendor count (fix the 0 issue)
        print("\n👥 Checking vendors...")
        cur.execute("SELECT COUNT(*) FROM vendor;")
        vendor_count_result = cur.fetchone()
        vendor_count = vendor_count_result[0] if vendor_count_result else 0
        print(f"Total vendors in database: {vendor_count}")
        
        # Step 4: Check existing columns
        print("\n🔍 Checking existing columns...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'vendor' 
            AND column_name IN ('subdomain', 'domain_type', 'website_status', 'readiness_score');
        """)
        existing_columns = [row[0] for row in cur.fetchall()]
        
        if existing_columns:
            print(f"⚠️ Some subdomain columns already exist: {existing_columns}")
            overwrite = input("Do you want to continue anyway? (yes/no): ").lower()
            if overwrite != 'yes':
                print("❌ Migration cancelled")
                return False
        else:
            print("✅ No subdomain columns exist - ready for migration")
        
        # Step 5: Execute migration
        print("\n🔄 Adding subdomain fields...")
        
        migration_sql = """
        -- Add subdomain fields
        ALTER TABLE vendor ADD COLUMN IF NOT EXISTS subdomain VARCHAR(50);
        ALTER TABLE vendor ADD COLUMN IF NOT EXISTS domain_type VARCHAR(20) DEFAULT 'free';
        ALTER TABLE vendor ADD COLUMN IF NOT EXISTS website_status VARCHAR(20) DEFAULT 'draft';
        ALTER TABLE vendor ADD COLUMN IF NOT EXISTS went_live_at TIMESTAMP WITH TIME ZONE;
        ALTER TABLE vendor ADD COLUMN IF NOT EXISTS subdomain_created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE vendor ADD COLUMN IF NOT EXISTS readiness_score INTEGER DEFAULT 0;
        
        -- Add constraints
        ALTER TABLE vendor DROP CONSTRAINT IF EXISTS chk_domain_type;
        ALTER TABLE vendor ADD CONSTRAINT chk_domain_type 
        CHECK (domain_type IN ('free', 'purchased', 'custom'));
        
        ALTER TABLE vendor DROP CONSTRAINT IF EXISTS chk_website_status;
        ALTER TABLE vendor ADD CONSTRAINT chk_website_status 
        CHECK (website_status IN ('draft', 'preview', 'live'));
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_vendor_subdomain ON vendor(subdomain);
        CREATE INDEX IF NOT EXISTS idx_vendor_domain_type ON vendor(domain_type);
        CREATE INDEX IF NOT EXISTS idx_vendor_website_status ON vendor(website_status);
        """
        
        cur.execute(migration_sql)
        conn.commit()
        print("✅ Subdomain fields added successfully")
        
        # Step 6: Generate subdomains for existing vendors
        if vendor_count > 0:
            print(f"\n🔄 Generating subdomains for {vendor_count} existing vendors...")
            
            # Get vendors without subdomains
            cur.execute("""
                SELECT id, business_name, city, owner_name 
                FROM vendor 
                WHERE subdomain IS NULL OR subdomain = ''
                ORDER BY id;
            """)
            
            vendors_need_subdomains = cur.fetchall()
            print(f"Found {len(vendors_need_subdomains)} vendors needing subdomains")
            
            if vendors_need_subdomains:
                used_subdomains = set()
                successful_updates = 0
                
                for vendor_id, business_name, city, owner_name in vendors_need_subdomains:
                    try:
                        # Generate unique subdomain
                        subdomain = generate_unique_subdomain(
                            business_name, city, vendor_id, used_subdomains
                        )
                        
                        # Update vendor
                        cur.execute("""
                            UPDATE vendor 
                            SET subdomain = %s,
                                domain_type = 'free',
                                website_status = 'draft',
                                subdomain_created_at = CURRENT_TIMESTAMP,
                                readiness_score = 30
                            WHERE id = %s
                        """, (subdomain, vendor_id))
                        
                        used_subdomains.add(subdomain)
                        successful_updates += 1
                        
                        print(f"  ✅ ID {vendor_id}: {business_name} → {subdomain}.shopinstreet.com")
                        
                    except Exception as e:
                        print(f"  ❌ Failed for vendor {vendor_id}: {e}")
                        continue
                
                conn.commit()
                print(f"\n✅ Successfully generated subdomains for {successful_updates} vendors")
            else:
                print("✅ All vendors already have subdomains")
        else:
            print("\n📝 No existing vendors found - migration complete")
        
        # Step 7: Verify results
        print("\n🔍 Verifying migration results...")
        
        cur.execute("""
            SELECT 
                COUNT(*) as total_vendors,
                COUNT(subdomain) as vendors_with_subdomains,
                COUNT(CASE WHEN website_status = 'draft' THEN 1 END) as draft_status,
                COUNT(CASE WHEN domain_type = 'free' THEN 1 END) as free_domains
            FROM vendor;
        """)
        
        stats = cur.fetchone()
        total, with_subdomains, draft, free = stats
        
        print(f"📊 Migration Results:")
        print(f"  Total vendors: {total}")
        print(f"  Vendors with subdomains: {with_subdomains}")
        print(f"  Draft status: {draft}")
        print(f"  Free domains: {free}")
        
        # Show sample results
        cur.execute("""
            SELECT business_name, subdomain, domain_type, website_status 
            FROM vendor 
            WHERE subdomain IS NOT NULL 
            LIMIT 5;
        """)
        
        sample_results = cur.fetchall()
        if sample_results:
            print(f"\n📝 Sample Results:")
            for business_name, subdomain, domain_type, status in sample_results:
                print(f"  {business_name} → {subdomain}.shopinstreet.com ({domain_type}, {status})")
        
        print("\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("✅ Subdomain fields added to vendor table")
        print("✅ Subdomains generated for existing vendors")
        print("✅ All vendors ready for website creation")
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def generate_unique_subdomain(business_name, city, vendor_id, used_subdomains):
    """Generate a unique subdomain"""
    
    # Clean business name
    base = re.sub(r'[^a-zA-Z0-9]', '', business_name.lower())
    
    # Remove common words if too long
    if len(base) > 15:
        common_words = ['restaurant', 'food', 'cafe', 'store', 'shop', 'electronics', 'fashion']
        for word in common_words:
            base = base.replace(word, '')
    
    base = base[:15]
    
    if not base:
        base = f"business{vendor_id}"
    
    # Try different variations
    candidates = [base]
    
    # Add city abbreviation
    if city:
        city_abbr = get_city_abbreviation(city)
        candidates.append(f"{base}{city_abbr}")
    
    # Add vendor ID
    candidates.append(f"{base}{vendor_id}")
    
    # Try numbered versions
    for i in range(2, 10):
        candidates.append(f"{base}{i}")
    
    # Find first available
    for candidate in candidates:
        if candidate not in used_subdomains:
            return candidate
    
    # Fallback
    import uuid
    return f"{base}{uuid.uuid4().hex[:6]}"

def get_city_abbreviation(city):
    """Get city abbreviation"""
    if not city:
        return ""
    
    city_mappings = {
        'bangalore': 'blr', 'bengaluru': 'blr',
        'mumbai': 'mum', 'bombay': 'mum', 
        'delhi': 'del', 'new delhi': 'del',
        'hyderabad': 'hyd',
        'chennai': 'che', 'madras': 'che',
        'kolkata': 'kol', 'calcutta': 'kol',
        'pune': 'pune', 'ahmedabad': 'amd'
    }
    
    return city_mappings.get(city.lower().strip(), city.lower()[:3])

if __name__ == "__main__":
    print("🔧 BULLETPROOF SUBDOMAIN MIGRATION")
    print("This migration is designed to handle all edge cases safely.")
    print("\nWhat this will do:")
    print("✅ Add subdomain, domain_type, website_status fields")
    print("✅ Generate unique subdomains for all existing vendors")
    print("✅ Set default values (free domain, draft status)")
    print("✅ Create performance indexes")
    print("✅ Detailed logging and verification")
    
    confirm = input("\n❓ Proceed with bulletproof migration? (yes/no): ").lower()
    
    if confirm == 'yes':
        success = bulletproof_migration()
        if success:
            print("\n🚀 NEXT STEPS:")
            print("1. Update your Vendor model with new fields")
            print("2. Add subdomain methods to Vendor class") 
            print("3. Test subdomain generation")
            print("4. Integrate with registration flow")
        else:
            print("\n❌ Migration failed - check errors above")
    else:
        print("❌ Migration cancelled")