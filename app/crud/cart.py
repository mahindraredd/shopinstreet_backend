from sqlalchemy.orm import Session
from app.models import models

def add_to_cart(db: Session, user_id: int, product_id: int, quantity: int):
    item = models.CartItem(user_id=user_id, product_id=product_id, quantity=quantity, status='in_cart')
    db.add(item)
    db.commit()
    return item

def get_cart(db: Session, user_id: int):
    return db.query(models.CartItem).filter(models.CartItem.user_id == user_id).all()
