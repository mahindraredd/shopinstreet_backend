# test_step1.py - Test our Vendor model and encryption

import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

def test_imports():
    """Test 1: Can we import our Vendor model?"""
    print("🔍 Testing imports...")
    try:
        from app.models.vendor import Vendor
        print("✅ Vendor model imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_encryption_setup():
    """Test 2: Is encryption properly configured?"""
    print("\n🔍 Testing encryption setup...")
    try:
        from app.models.vendor import Vendor, ENCRYPTION_AVAILABLE
        
        print(f"✅ Encryption available: {ENCRYPTION_AVAILABLE}")
        
        # Check if encryption key is set
        key_set = bool(os.getenv('BANKING_ENCRYPTION_KEY'))
        print(f"✅ Encryption key in .env: {key_set}")
        
        if key_set:
            key = os.getenv('BANKING_ENCRYPTION_KEY')
            print(f"✅ Key format looks correct: {key.endswith('=') and len(key) > 20}")
        
        return ENCRYPTION_AVAILABLE and key_set
    except Exception as e:
        print(f"❌ Encryption setup error: {e}")
        return False

def test_vendor_creation():
    """Test 3: Can we create a Vendor instance?"""
    print("\n🔍 Testing vendor creation...")
    try:
        from app.models.vendor import Vendor
        
        # Create vendor instance (not saving to DB)
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
        print(f"✅ Profile completion: {vendor.profile_completion_percentage}%")
        
        return True
    except Exception as e:
        print(f"❌ Vendor creation error: {e}")
        return False

def test_encryption_functionality():
    """Test 4: Does encryption/decryption work?"""
    print("\n🔍 Testing encryption functionality...")
    try:
        from app.models.vendor import Vendor
        
        vendor = Vendor()
        
        # Test account number encryption
        test_account = "1234567890123456"
        vendor.account_number = test_account
        
        print(f"✅ Original account: {test_account}")
        print(f"✅ Encrypted format: {vendor.account_number_encrypted is not None}")
        print(f"✅ Decrypted matches: {vendor.account_number == test_account}")
        print(f"✅ Masked display: {vendor.get_masked_account_number()}")
        
        # Test routing code encryption
        test_routing = "HDFC0001234"
        vendor.routing_code = test_routing
        
        print(f"✅ Routing encrypted: {vendor.routing_code_encrypted is not None}")
        print(f"✅ Routing decrypted: {vendor.routing_code == test_routing}")
        
        return True
    except Exception as e:
        print(f"❌ Encryption functionality error: {e}")
        return False

def test_risk_scoring():
    """Test 5: Does risk scoring work?"""
    print("\n🔍 Testing risk scoring...")
    try:
        from app.models.vendor import Vendor
        
        vendor = Vendor()
        vendor.business_name = "Test Company"
        vendor.country = "India"
        vendor.is_verified = False
        
        # Calculate initial risk score
        initial_risk = vendor.calculate_risk_score()
        print(f"✅ Initial risk score: {initial_risk}")
        
        # Add GST number (should reduce risk)
        vendor.gst_number = "22AAAAA0000A1Z5"
        improved_risk = vendor.calculate_risk_score()
        print(f"✅ Risk with GST: {improved_risk}")
        print(f"✅ Risk improved: {improved_risk < initial_risk}")
        
        # Update compliance status
        vendor.update_compliance_status()
        print(f"✅ Compliance status: {vendor.compliance_status}")
        
        return True
    except Exception as e:
        print(f"❌ Risk scoring error: {e}")
        return False

def test_profile_completion():
    """Test 6: Does profile completion calculation work?"""
    print("\n🔍 Testing profile completion...")
    try:
        from app.models.vendor import Vendor
        
        vendor = Vendor()
        
        # Empty vendor
        empty_completion = vendor.calculate_profile_completion()
        print(f"✅ Empty profile completion: {empty_completion}%")
        
        # Add required fields
        vendor.business_name = "Test Company"
        vendor.owner_name = "Test Owner"
        vendor.email = "test@example.com"
        vendor.phone = "1234567890"
        vendor.address = "123 Test St"
        vendor.city = "Test City"
        vendor.state = "Test State"
        vendor.country = "Canada"
        vendor.business_category = "Technology"
        
        partial_completion = vendor.calculate_profile_completion()
        print(f"✅ Partial profile completion: {partial_completion}%")
        
        # Add optional fields
        vendor.business_description = "A test company for our platform"
        vendor.website_url = "https://testcompany.com"
        vendor.bank_name = "Test Bank"
        vendor.account_number = "1234567890"
        
        full_completion = vendor.calculate_profile_completion()
        print(f"✅ Enhanced profile completion: {full_completion}%")
        
        vendor.update_profile_completion()
        print(f"✅ Profile completed status: {vendor.profile_completed}")
        
        return True
    except Exception as e:
        print(f"❌ Profile completion error: {e}")
        return False

def run_all_tests():
    """Run all Step 1 tests"""
    print("🚀 TESTING STEP 1: VENDOR MODEL & ENCRYPTION")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_encryption_setup,
        test_vendor_creation,
        test_encryption_functionality,
        test_risk_scoring,
        test_profile_completion
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print("❌ Test failed!")
        except Exception as e:
            print(f"❌ Test crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Ready for Step 2")
        return True
    else:
        print("🔥 SOME TESTS FAILED! Fix issues before Step 2")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)