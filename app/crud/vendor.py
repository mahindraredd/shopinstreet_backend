from sqlalchemy.orm import Session
from app.models.vendor import Vendor

# ✅ Check if vendor exists
def get_vendor_by_email_or_phone(db: Session, email: str, phone: str):
    return db.query(Vendor).filter((Vendor.email == email) | (Vendor.phone == phone)).first()

# ✅ Create vendor
def create_vendor(db: Session, vendor: Vendor):
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor

# ✅ Get vendor by email
def get_vendor_by_email(db: Session, email: str):
    return db.query(Vendor).filter(Vendor.email == email).first()
