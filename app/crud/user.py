from sqlalchemy.orm import Session
from app.models import models
from app.schemas.schemas import UserSignup
from app.utils.utils import hash_password

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user_data: UserSignup):
    hashed_pwd = hash_password(user_data.password)
    user_data.password = hashed_pwd
    new_user = models.User(**user_data.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
