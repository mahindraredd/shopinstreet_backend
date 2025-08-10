from fastapi import logger

from app.models.vendor import Vendor
# app/models/vendor.py - FIXED ENTERPRISE VERSION

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base
import os
import base64
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric
from sqlalchemy.sql import func
from datetime import datetime
import re
import logging

class VendorWebsiteService:
    """Service for managing vendor websites and subdomains"""
    
    @staticmethod
    def get_vendor_website_info(vendor_id: int, db_session):
        """Get complete website information for a vendor"""
        try:
            vendor = db_session.query(Vendor).filter(Vendor.id == vendor_id).first()
            if not vendor:
                return {"error": "Vendor not found"}
            
            # Ensure vendor has subdomain
            if not vendor.subdomain:
                vendor.update_subdomain_if_needed(db_session)
                db_session.commit()
            
            # Calculate current readiness
            current_score = vendor.calculate_readiness_score()
            db_session.commit()  # Save updated score
            
            return {
                "success": True,
                "vendor_id": vendor.id,
                "business_name": vendor.business_name,
                "website_info": vendor.get_dashboard_summary()
            }
            
        except Exception as e:
            logger.error(f"Error getting vendor website info: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def go_live_vendor_website(vendor_id: int, db_session):
        """Make vendor website live"""
        try:
            vendor = db_session.query(Vendor).filter(Vendor.id == vendor_id).first()
            if not vendor:
                return {"error": "Vendor not found"}
            
            # Attempt to go live
            result = vendor.go_live()
            
            if result["success"]:
                db_session.commit()
                logger.info(f"Vendor {vendor_id} website went live: {vendor.get_website_url()}")
            
            return result
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Error making vendor {vendor_id} go live: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def update_vendor_readiness(vendor_id: int, db_session):
        """Update and return vendor readiness score"""
        try:
            vendor = db_session.query(Vendor).filter(Vendor.id == vendor_id).first()
            if not vendor:
                return {"error": "Vendor not found"}
            
            score = vendor.calculate_readiness_score()
            db_session.commit()
            
            return {
                "success": True,
                "vendor_id": vendor.id,
                "readiness_score": score,
                "can_go_live": vendor.can_go_live(),
                "next_steps": vendor.get_next_steps()
            }
            
        except Exception as e:
            logger.error(f"Error updating vendor {vendor_id} readiness: {e}")
            return {"error": str(e)}