
import logging
import asyncio
from sqlalchemy.orm import Session
from app.models.vendor import Vendor
from app.models.domain import VendorDomain, DomainType, DomainStatus
from typing import Dict, Optional, Any
import os
import json
from pathlib import Path
from jinja2 import Template
import uuid

logger = logging.getLogger(__name__)

class VendorTemplateService:
    """Service for automatically deploying templates to vendor subdomains"""
    
    def __init__(self):
        self.templates_base_path = "static/vendor_templates"
        self.hosting_base_path = "static/hosted_sites"
        
    async def deploy_default_template_for_vendor(
        self, 
        db: Session, 
        vendor: Vendor, 
        template_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Deploy default template automatically when vendor registers
        """
        try:
            # Default to template 1 if none specified
            if template_id is None:
                template_id = self._get_default_template_for_business(vendor.business_category)
            
            logger.info(f"Deploying template {template_id} for vendor {vendor.id}")
            
            # Step 1: Create vendor domain record
            domain_record = await self._create_vendor_domain_record(db, vendor, template_id)
            
            # Step 2: Generate static website from template
            website_content = await self._generate_website_from_template(vendor, template_id)
            
            # Step 3: Deploy to hosting directory
            deployment_result = await self._deploy_to_hosting(vendor, website_content)
            
            # Step 4: Update domain status
            domain_record.status = DomainStatus.ACTIVE
            domain_record.hosting_active = True
            db.commit()
            
            # Step 5: Update vendor website status
            vendor.website_status = 'active'
            vendor.readiness_score = vendor.calculate_readiness_score()
            db.commit()
            
            logger.info(f"Template deployment successful for vendor {vendor.id}")
            
            return {
                "success": True,
                "template_id": template_id,
                "website_url": vendor.get_website_url(),
                "deployment_path": deployment_result["path"],
                "message": "Template deployed successfully"
            }
            
        except Exception as e:
            logger.error(f"Template deployment failed for vendor {vendor.id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Template deployment failed"
            }
    
    def _get_default_template_for_business(self, business_category: str) -> int:
        """Get appropriate default template based on business category"""
        template_mapping = {
            "restaurant": 3,  # Restaurant template
            "food": 3,
            "retail": 2,      # E-commerce template
            "ecommerce": 2,
            "services": 1,    # Business template
            "consulting": 1,
            "technology": 1,
            "creative": 4,    # Portfolio template
            "photography": 4,
            "art": 4
        }
        
        category_lower = business_category.lower() if business_category else ""
        
        # Check for partial matches
        for key, template_id in template_mapping.items():
            if key in category_lower:
                return template_id
        
        # Default to business template
        return 1
    
    async def _create_vendor_domain_record(
        self, 
        db: Session, 
        vendor: Vendor, 
        template_id: int
    ) -> VendorDomain:
        """Create domain record for vendor subdomain"""
        
        domain_record = VendorDomain(
            vendor_id=vendor.id,
            domain_name=f"{vendor.subdomain}.vision.com",
            domain_type=DomainType.SUBDOMAIN,
            status=DomainStatus.HOSTING_SETUP,
            template_id=template_id,
            ssl_enabled=True,  # Free SSL for subdomains
            dns_configured=True,  # Automatic for subdomains
            hosting_active=False  # Will be set to True after deployment
        )
        
        db.add(domain_record)
        db.commit()
        db.refresh(domain_record)
        
        return domain_record
    
    async def _generate_website_from_template(
        self, 
        vendor: Vendor, 
        template_id: int
    ) -> Dict[str, str]:
        """Generate website content from template using vendor data"""
        
        template_config = self._get_template_config(template_id)
        
        # Prepare vendor data for template
        template_data = {
            "business_name": vendor.business_name,
            "owner_name": vendor.owner_name,
            "business_category": vendor.business_category,
            "address": vendor.address,
            "city": vendor.city,
            "state": vendor.state,
            "pincode": vendor.pincode,
            "phone": vendor.phone,
            "email": vendor.email,
            "website_url": vendor.website_url,
            "linkedin_url": vendor.linkedin_url,
            "business_logo": vendor.business_logo,
            "subdomain": vendor.subdomain,
            "full_website_url": vendor.get_website_url(),
            
            # Generated content
            "meta_title": f"{vendor.business_name} - {vendor.business_category}",
            "meta_description": f"Welcome to {vendor.business_name}. Professional {vendor.business_category.lower()} services in {vendor.city}.",
            "hero_title": f"Welcome to {vendor.business_name}",
            "hero_subtitle": f"Professional {vendor.business_category} Services",
            
            # Default content based on business type
            "about_content": self._generate_about_content(vendor),
            "services": self._generate_default_services(vendor.business_category),
            "contact_info": {
                "address": f"{vendor.address}, {vendor.city}, {vendor.state} {vendor.pincode}",
                "phone": vendor.phone,
                "email": vendor.email
            }
        }
        
        # Load and render template files
        website_content = {}
        template_path = Path(self.templates_base_path) / f"template_{template_id}"
        
        for file_path in template_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in [".html", ".css", ".js"]:
                relative_path = file_path.relative_to(template_path)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Render template with vendor data
                template = Template(content)
                rendered_content = template.render(**template_data)
                
                website_content[str(relative_path)] = rendered_content
        
        return website_content
    
    async def _deploy_to_hosting(
        self, 
        vendor: Vendor, 
        website_content: Dict[str, str]
    ) -> Dict[str, Any]:
        """Deploy generated website to hosting directory"""
        
        # Create hosting directory
        hosting_path = Path(self.hosting_base_path) / vendor.subdomain
        hosting_path.mkdir(parents=True, exist_ok=True)
        
        # Write all files
        for file_path, content in website_content.items():
            full_path = hosting_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        logger.info(f"Website deployed to {hosting_path}")
        
        return {
            "path": str(hosting_path),
            "files_deployed": len(website_content),
            "url": f"https://{vendor.subdomain}.vision.com"
        }
    
    def _get_template_config(self, template_id: int) -> Dict[str, Any]:
        """Get template configuration"""
        templates = {
            1: {
                "name": "Modern Business",
                "category": "business",
                "files": ["index.html", "about.html", "services.html", "contact.html"],
                "styles": ["style.css", "responsive.css"],
                "scripts": ["main.js"]
            },
            2: {
                "name": "E-commerce Store",
                "category": "ecommerce", 
                "files": ["index.html", "products.html", "cart.html", "checkout.html"],
                "styles": ["ecommerce.css", "products.css"],
                "scripts": ["cart.js", "checkout.js"]
            },
            3: {
                "name": "Restaurant & Food",
                "category": "restaurant",
                "files": ["index.html", "menu.html", "order.html", "about.html"],
                "styles": ["restaurant.css", "menu.css"],
                "scripts": ["menu.js", "order.js"]
            },
            4: {
                "name": "Portfolio Showcase",
                "category": "portfolio",
                "files": ["index.html", "portfolio.html", "about.html", "contact.html"],
                "styles": ["portfolio.css", "gallery.css"],
                "scripts": ["gallery.js", "lightbox.js"]
            }
        }
        
        return templates.get(template_id, templates[1])
    
    def _generate_about_content(self, vendor: Vendor) -> str:
        """Generate default about content for vendor"""
        return f"""
        Welcome to {vendor.business_name}, your trusted partner in {vendor.business_category.lower()}.
        
        Located in {vendor.city}, {vendor.state}, we are committed to providing exceptional service 
        and quality to all our customers. Under the leadership of {vendor.owner_name}, our team 
        brings years of experience and dedication to every project.
        
        We believe in building lasting relationships with our clients through transparency, 
        reliability, and superior service delivery.
        """
    
    def _generate_default_services(self, business_category: str) -> list:
        """Generate default services based on business category"""
        service_templates = {
            "restaurant": [
                "Dine-in Service",
                "Takeaway Orders", 
                "Online Delivery",
                "Catering Services",
                "Special Events"
            ],
            "retail": [
                "Product Sales",
                "Customer Support",
                "Product Consultation",
                "After-sales Service",
                "Bulk Orders"
            ],
            "services": [
                "Consultation",
                "Implementation",
                "Support & Maintenance",
                "Training",
                "Custom Solutions"
            ],
            "technology": [
                "Software Development",
                "System Integration",
                "Technical Support",
                "Maintenance",
                "Consulting"
            ]
        }
        
        category_lower = business_category.lower() if business_category else ""
        
        for key, services in service_templates.items():
            if key in category_lower:
                return services
        
        # Default services
        return [
            "Professional Consultation",
            "Quality Service Delivery", 
            "Customer Support",
            "Maintenance & Support",
            "Custom Solutions"
        ]