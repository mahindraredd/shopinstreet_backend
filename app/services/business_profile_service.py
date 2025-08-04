# app/services/business_profile_service.py
"""
Business Profile Service - Enterprise Grade
Contains all business logic for managing vendor business profiles
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.vendor import Vendor
from app.schemas.business_profile import (
    BusinessProfileUpdateRequest, 
    ProfileCompletionResponse,
    ComplianceStatusResponse,
    CountryRequirementsResponse,
    FieldValidationResponse
)
from typing import Optional, Dict, Any, List, Tuple
import re
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class BusinessProfileService:
    """Enterprise service for managing vendor business profiles"""
    
    @staticmethod
    def get_business_profile(db: Session, vendor_id: int) -> Optional[Vendor]:
        """Get vendor business profile by ID with error handling"""
        try:
            vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
            if vendor:
                # Update profile completion on every fetch
                vendor.update_profile_completion()
                db.commit()
            return vendor
        except Exception as e:
            logger.error(f"Error fetching business profile for vendor {vendor_id}: {e}")
            return None
    
    @staticmethod
    def update_business_profile(
        db: Session, 
        vendor_id: int, 
        profile_data: BusinessProfileUpdateRequest,
        updated_by: Optional[int] = None
    ) -> Tuple[Optional[Vendor], List[str]]:
        """
        Update vendor business profile with validation and error handling
        Returns: (updated_vendor, validation_errors)
        """
        validation_errors = []
        
        try:
            vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
            if not vendor:
                validation_errors.append("Vendor not found")
                return None, validation_errors
            
            # Validate the update data
            validation_errors = BusinessProfileService._validate_profile_data(
                profile_data, vendor.country
            )
            
            if validation_errors:
                return None, validation_errors
            
            # Update only provided fields
            update_data = profile_data.dict(exclude_unset=True)
            
            for field, value in update_data.items():
                if hasattr(vendor, field) and value is not None:
                    setattr(vendor, field, value)
            
            # Update metadata
            vendor.profile_updated_at = datetime.utcnow()
            if updated_by:
                vendor.profile_updated_by = updated_by
            
            # Recalculate profile completion and risk
            vendor.update_profile_completion()
            vendor.update_compliance_status()
            
            db.commit()
            db.refresh(vendor)
            
            logger.info(f"Business profile updated for vendor {vendor_id}")
            return vendor, []
            
        except Exception as e:
            logger.error(f"Error updating business profile for vendor {vendor_id}: {e}")
            db.rollback()
            validation_errors.append(f"Update failed: {str(e)}")
            return None, validation_errors
    
    @staticmethod
    def update_banking_info(
        db: Session,
        vendor_id: int,
        bank_name: Optional[str] = None,
        account_number: Optional[str] = None,
        routing_code: Optional[str] = None,
        account_holder_name: Optional[str] = None
    ) -> Tuple[Optional[Vendor], List[str]]:
        """
        Update sensitive banking information with encryption
        Returns: (updated_vendor, validation_errors)
        """
        validation_errors = []
        
        try:
            vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
            if not vendor:
                validation_errors.append("Vendor not found")
                return None, validation_errors
            
            # Validate banking info based on country
            banking_errors = BusinessProfileService._validate_banking_info(
                vendor.country, account_number, routing_code
            )
            validation_errors.extend(banking_errors)
            
            if validation_errors:
                return None, validation_errors
            
            # Update banking fields (encryption happens automatically via property setters)
            if bank_name is not None:
                vendor.bank_name = bank_name
            if account_number is not None:
                vendor.account_number = account_number  # Encrypted automatically
            if routing_code is not None:
                vendor.routing_code = routing_code  # Encrypted automatically
            if account_holder_name is not None:
                vendor.account_holder_name = account_holder_name
            
            # Update metadata
            vendor.profile_updated_at = datetime.utcnow()
            vendor.update_profile_completion()
            vendor.update_compliance_status()
            
            db.commit()
            db.refresh(vendor)
            
            logger.info(f"Banking information updated for vendor {vendor_id}")
            return vendor, []
            
        except Exception as e:
            logger.error(f"Error updating banking info for vendor {vendor_id}: {e}")
            db.rollback()
            validation_errors.append(f"Banking update failed: {str(e)}")
            return None, validation_errors
    
    @staticmethod
    def get_profile_completion_status(vendor: Vendor) -> ProfileCompletionResponse:
        """Get detailed profile completion status"""
        
        # Define sections and their required fields
        sections = {
            "Basic Information": [
                vendor.business_name, vendor.owner_name, vendor.email, 
                vendor.phone, vendor.business_category
            ],
            "Address Information": [
                vendor.address, vendor.city, vendor.state, 
                vendor.pincode, vendor.country
            ],
            "Business Details": [
                vendor.business_type, vendor.business_description
            ],
            "Tax Information": [
                vendor.gst_number if vendor.country == "India" else vendor.hst_pst_number,
            ],
            "Banking Information": [
                vendor.bank_name, vendor.account_number, 
                vendor.routing_code, vendor.account_holder_name
            ],
            "Optional Information": [
                vendor.website_url, vendor.alternate_email
            ]
        }
        
        completed_sections = []
        missing_sections = []
        priority_missing = []
        
        for section_name, fields in sections.items():
            section_complete = all(field and str(field).strip() for field in fields)
            if section_complete:
                completed_sections.append(section_name)
            else:
                missing_sections.append(section_name)
                if section_name in ["Basic Information", "Address Information", "Tax Information"]:
                    priority_missing.append(section_name)
        
        # Determine next action
        next_action = "Profile Complete!"
        if priority_missing:
            next_action = f"Complete {priority_missing[0]} section"
        elif missing_sections:
            next_action = f"Complete {missing_sections[0]} section"
        
        return ProfileCompletionResponse(
            completion_percentage=vendor.profile_completion_percentage,
            is_profile_complete=vendor.profile_completed,
            completed_sections=completed_sections,
            missing_sections=missing_sections,
            next_recommended_action=next_action,
            priority_missing_fields=priority_missing
        )
    
    @staticmethod
    def get_compliance_status(vendor: Vendor) -> ComplianceStatusResponse:
        """Get detailed compliance status"""
        
        issues = []
        recommendations = []
        
        # Check for compliance issues
        if not vendor.is_verified:
            issues.append("Account not verified")
            recommendations.append("Complete email/phone verification")
        
        if vendor.country == "India" and not vendor.gst_number:
            issues.append("Missing GST number")
            recommendations.append("Add valid GST number for India")
        
        if vendor.country == "Canada" and not vendor.hst_pst_number:
            issues.append("Missing HST/PST number")
            recommendations.append("Add valid HST/PST number for Canada")
        
        if not vendor.bank_name or not vendor.account_number:
            issues.append("Incomplete banking information")
            recommendations.append("Complete banking details for payments")
        
        if vendor.risk_score > 70:
            issues.append("High risk score")
            recommendations.append("Complete profile information to reduce risk")
        
        return ComplianceStatusResponse(
            risk_score=vendor.risk_score,
            compliance_status=vendor.compliance_status,
            last_check=vendor.last_compliance_check,
            compliance_issues=issues,
            recommendations=recommendations
        )
    
    @staticmethod
    def get_country_requirements(country: str) -> CountryRequirementsResponse:
        """Get country-specific field requirements"""
        
        requirements_map = {
            "India": CountryRequirementsResponse(
                country="India",
                required_tax_fields=["gst_number", "pan_card"],
                optional_tax_fields=["business_registration_number"],
                banking_requirements={
                    "routing_code": "IFSC Code (11 characters)",
                    "account_number": "10-18 digit account number",
                    "format": "Indian banking standards"
                },
                sample_formats={
                    "gst_number": "22AAAAA0000A1Z5",
                    "pan_card": "ABCDE1234F",
                    "ifsc_code": "HDFC0001234"
                },
                supported_currencies=["INR", "USD"]
            ),
            "Canada": CountryRequirementsResponse(
                country="Canada",
                required_tax_fields=["hst_pst_number"],
                optional_tax_fields=["business_registration_number"],
                banking_requirements={
                    "routing_code": "9-digit routing number",
                    "account_number": "7-12 digit account number",
                    "format": "Canadian banking standards"
                },
                sample_formats={
                    "hst_pst_number": "123456789RT0001",
                    "routing_number": "000012345"
                },
                supported_currencies=["CAD", "USD"]
            ),
            "United States": CountryRequirementsResponse(
                country="United States",
                required_tax_fields=["business_registration_number"],
                optional_tax_fields=["tax_exemption_status"],
                banking_requirements={
                    "routing_code": "9-digit routing number",
                    "account_number": "4-17 digit account number",
                    "format": "US banking standards"
                },
                sample_formats={
                    "routing_number": "021000021",
                    "account_number": "1234567890"
                },
                supported_currencies=["USD"]
            )
        }
        
        return requirements_map.get(country, CountryRequirementsResponse(
            country=country,
            required_tax_fields=[],
            optional_tax_fields=["business_registration_number"],
            banking_requirements={},
            sample_formats={},
            supported_currencies=["USD"]
        ))
    
    @staticmethod
    def validate_field(field_name: str, field_value: str, country: str = "US") -> FieldValidationResponse:
        """Validate individual field values"""
        
        validators = {
            "gst_number": BusinessProfileService._validate_gst_number,
            "pan_card": BusinessProfileService._validate_pan_card,
            "hst_pst_number": BusinessProfileService._validate_hst_pst_number,
            "email": BusinessProfileService._validate_email,
            "phone": BusinessProfileService._validate_phone,
            "website_url": BusinessProfileService._validate_website
        }
        
        if field_name not in validators:
            return FieldValidationResponse(
                field_name=field_name,
                is_valid=True,
                error_message=None
            )
        
        try:
            is_valid, error_msg, suggestions = validators[field_name](field_value, country)
            return FieldValidationResponse(
                field_name=field_name,
                is_valid=is_valid,
                error_message=error_msg,
                suggestions=suggestions
            )
        except Exception as e:
            return FieldValidationResponse(
                field_name=field_name,
                is_valid=False,
                error_message=f"Validation error: {str(e)}"
            )
    
    @staticmethod
    def search_vendors_by_profile(
        db: Session,
        business_type: Optional[str] = None,
        country: Optional[str] = None,
        compliance_status: Optional[str] = None,
        min_completion: Optional[int] = None,
        max_risk_score: Optional[int] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[Vendor], int]:
        """Search vendors by profile criteria with pagination"""
        
        try:
            query = db.query(Vendor)
            
            # Apply filters
            filters = []
            
            if business_type:
                filters.append(Vendor.business_type == business_type)
            
            if country:
                filters.append(Vendor.country == country)
            
            if compliance_status:
                filters.append(Vendor.compliance_status == compliance_status)
            
            if min_completion is not None:
                filters.append(Vendor.profile_completion_percentage >= min_completion)
            
            if max_risk_score is not None:
                filters.append(Vendor.risk_score <= max_risk_score)
            
            if filters:
                query = query.filter(and_(*filters))
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * page_size
            vendors = query.offset(offset).limit(page_size).all()
            
            return vendors, total
            
        except Exception as e:
            logger.error(f"Error searching vendors: {e}")
            return [], 0
    
    # Private validation methods
    @staticmethod
    def _validate_profile_data(data: BusinessProfileUpdateRequest, country: str) -> List[str]:
        """Validate profile update data"""
        errors = []
        
        # Email validation
        if data.email and not BusinessProfileService._validate_email(data.email, country)[0]:
            errors.append("Invalid email format")
        
        # Phone validation
        if data.phone and not BusinessProfileService._validate_phone(data.phone, country)[0]:
            errors.append("Invalid phone number format")
        
        # Country-specific validations
        if country == "India":
            if data.gst_number and not BusinessProfileService._validate_gst_number(data.gst_number, country)[0]:
                errors.append("Invalid GST number format")
            if data.pan_card and not BusinessProfileService._validate_pan_card(data.pan_card, country)[0]:
                errors.append("Invalid PAN card format")
        
        return errors
    
    @staticmethod
    def _validate_banking_info(country: str, account_number: Optional[str], routing_code: Optional[str]) -> List[str]:
        """Validate banking information based on country"""
        errors = []
        
        if account_number:
            if len(account_number) < 4 or len(account_number) > 20:
                errors.append("Account number must be between 4-20 characters")
        
        if routing_code:
            if country == "India":
                if len(routing_code) != 11:
                    errors.append("IFSC code must be 11 characters")
            elif country in ["Canada", "United States"]:
                if len(routing_code) != 9 or not routing_code.isdigit():
                    errors.append("Routing number must be 9 digits")
        
        return errors
    
    @staticmethod
    def _validate_gst_number(value: str, country: str) -> Tuple[bool, Optional[str], List[str]]:
        """Validate GST number format"""
        if not value:
            return True, None, []
        
        pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
        if re.match(pattern, value):
            return True, None, []
        else:
            return False, "Invalid GST number format", ["Format: 22AAAAA0000A1Z5"]
    
    @staticmethod
    def _validate_pan_card(value: str, country: str) -> Tuple[bool, Optional[str], List[str]]:
        """Validate PAN card format"""
        if not value:
            return True, None, []
        
        pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
        if re.match(pattern, value):
            return True, None, []
        else:
            return False, "Invalid PAN card format", ["Format: ABCDE1234F"]
    
    @staticmethod
    def _validate_hst_pst_number(value: str, country: str) -> Tuple[bool, Optional[str], List[str]]:
        """Validate HST/PST number format"""
        if not value:
            return True, None, []
        
        # Basic validation - can be enhanced based on provincial requirements
        if len(value) >= 9:
            return True, None, []
        else:
            return False, "Invalid HST/PST number format", ["Contact tax authority for format"]
    
    @staticmethod
    def _validate_email(value: str, country: str) -> Tuple[bool, Optional[str], List[str]]:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, value):
            return True, None, []
        else:
            return False, "Invalid email format", ["Use format: user@domain.com"]
    
    @staticmethod
    def _validate_phone(value: str, country: str) -> Tuple[bool, Optional[str], List[str]]:
        """Validate phone number format"""
        # Remove spaces and special characters for validation
        clean_phone = re.sub(r'[\s\-\(\)]', '', value)
        
        if len(clean_phone) >= 10 and clean_phone.replace('+', '').isdigit():
            return True, None, []
        else:
            return False, "Invalid phone format", ["Use format: +1234567890"]
    
    @staticmethod
    def _validate_website(value: str, country: str) -> Tuple[bool, Optional[str], List[str]]:
        """Validate website URL format"""
        pattern = r'^https?://.+'
        if re.match(pattern, value):
            return True, None, []
        else:
            return False, "Invalid website URL", ["Use format: https://example.com"]