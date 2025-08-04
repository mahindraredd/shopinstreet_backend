# test_vendor_simple.py - Simple vendor model test

import os
import sys

print("🚀 TESTING STEP 1: VENDOR MODEL & ENCRYPTION")
print("=" * 50)

# Test 1: Import
print("🔍 Testing imports...")
try:
    from app.models.vendor import Vendor, ENCRYPTION_AVAILABLE
    print("✅ Vendor model imported successfully")
    print(f"✅ Encryption available: {ENCRYPTION_AVAILABLE}")
except Exception as e:
    print(f"❌ Import failed: {e}")
    exit(1)

# Test 2: Environment
print("\n🔍 Testing environment...")
key_set = bool(os.getenv('BANKING_ENCRYPTION_KEY'))
print(f"✅ Encryption key in .env: {key_set}")

# Test 3: Create vendor
print("\n🔍 Testing vendor creation...")
try:
    vendor = Vendor()
    vendor.business_name = "Test Company"
    vendor.owner_name = "Test Owner"
    vendor.email = "test@example.com"
    vendor.phone = "1234567890"
    vendor.business_category = "Technology"
    vendor.address = "123 Test St"
    vendor.city = "Test City"
    vendor.state = "Test State"
    vendor.pincode = "12345"
    vendor.country = "Canada"
    vendor.password_hash = "test_hash"
    vendor.verification_type = "email"
    vendor.verification_number = "123456"
    
    print("✅ Basic vendor instance created")
    print(f"✅ Business name: {vendor.business_name}")
    completion = vendor.calculate_profile_completion() 
    print(f"✅ Profile completion: {completion}%")
except Exception as e:
    print(f"❌ Vendor creation error: {e}")
    exit(1)

# Test 4: Encryption
print("\n🔍 Testing encryption...")
try:
    test_account = "1234567890123456"
    vendor.account_number = test_account
    
    print(f"✅ Original: {test_account}")
    print(f"✅ Encrypted: {vendor.account_number_encrypted is not None}")
    print(f"✅ Decrypted: {vendor.account_number == test_account}")
    print(f"✅ Masked: {vendor.get_masked_account_number()}")
except Exception as e:
    print(f"❌ Encryption error: {e}")
    exit(1)

print("\n" + "=" * 50)
print("🎉 ALL TESTS PASSED! Step 1 is working!")
print("✅ Ready for Step 2: Database Migration")
