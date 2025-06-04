from app.models import models
from sqlalchemy.orm import Session

def save_shipping_details(db: Session, user_id: int, data):
    shipping_info = models.ShippingDetails(
        user_id=user_id,
        full_name=data.full_name,
        address=data.address,
        city=data.city,
        state=data.state,
        pincode=data.pincode,
        phone=data.phone
    )
    db.add(shipping_info)

    # Mark cart items as part of order (you can extend with order model)
    cart_items = db.query(models.CartItem).filter(models.CartItem.user_id == user_id).all()
    if not cart_items:
        raise Exception("Cart is empty")

    # You can optionally create an Order model and link it here
    db.commit()
    return {"message": "Order placed successfully"}
