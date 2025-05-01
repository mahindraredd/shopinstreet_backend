from sqlalchemy.orm import Session
from app.models.order import Order, OrderItem
from app.schemas.order import OrderCreate

def create_order(db: Session, order_data: OrderCreate, vendor_id: int):
    order = Order(
        customer_name=order_data.customer_name,
        customer_email=order_data.customer_email,
        customer_phone=order_data.customer_phone,
        shipping_address=order_data.shipping_address,
        total_amount=order_data.total_amount,
        vendor_id=vendor_id
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    for item in order_data.order_items:
        db_item = OrderItem(
            product_id=item.product_id,
            product_name=item.product_name,
            quantity=item.quantity,
            price=item.price,
            order_id=order.id
        )
        db.add(db_item)
    db.commit()
    return order

def get_orders_by_vendor(db: Session, vendor_id: int):
    return db.query(Order).filter(Order.vendor_id == vendor_id).all()

def update_order_status(db: Session, order_id: int, new_status: str):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None
    order.status = new_status
    db.commit()
    db.refresh(order)
    return order

