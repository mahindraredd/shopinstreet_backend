from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.vendor import Vendor


# ✅ Add this below the instance
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/vendor/login")
# Dependency to get DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get the current vendor from token
def get_current_vendor(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Vendor:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    vendor = db.query(Vendor).filter(Vendor.email == email).first()
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    return vendor
