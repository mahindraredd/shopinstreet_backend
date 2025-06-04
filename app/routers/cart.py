from app.schemas.schemas import UserSignup, CartItemCreate, ShippingInfo
from app.crud import user, cart, shipping
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.schemas.order import OrderCreate, OrderItemCreate
from app.models.order import Order, OrderItem, OrderStatus
from sqlalchemy import func
from app.models.models import CartItem
from app.models.product import Product

router = APIRouter()

@router.post("/cart/add")
def add_item(data: CartItemCreate, user_id: int, db: Session = Depends(get_db)):
    return cart.add_to_cart(db, user_id, data.product_id, data.quantity)

@router.get("/cart")
def get_cart_items(user_id: int, db: Session = Depends(get_db)):
    return cart.get_cart(db, user_id)


@router.post("/checkout")
def checkout(user_id: int, data: ShippingInfo, db: Session = Depends(get_db)):
    # 1. Get active cart items for user
    cart_items = db.query(CartItem).filter(
        CartItem.user_id == user_id,
        CartItem.status == "in_cart"
    ).all()

    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # 2. Calculate total amount
    total_amount = 0
    order_items = []
    for item in cart_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            continue
        price = product.pricing_tiers[0].price if product.pricing_tiers else 0  # adjust this logic based on tier
        total_amount += price * item.quantity
        order_items.append(OrderItemCreate(
            product_id=product.id,
            product_name=product.name,
            quantity=item.quantity,
            price=price
        ))

    # 3. Create order
    new_order = Order(
        customer_name=data.full_name,
        customer_email=data.email,
        customer_phone=data.phone,
        shipping_address=f"{data.address}, {data.city}, {data.state} - {data.pincode}",
        total_amount=total_amount,
        status=OrderStatus.Pending
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # 4. Create OrderItems
    for item in order_items:
        db.add(OrderItem(
            order_id=new_order.id,
            product_id=item.product_id,
            product_name=item.product_name,
            quantity=item.quantity,
            price=item.price
        ))

    # 5. Update cart item statuses
    for item in cart_items:
        item.status = "checkout"

    db.commit()

    return {"message": "Order placed successfully", "order_id": new_order.id}