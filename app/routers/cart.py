from app.schemas.schemas import UserSignup, CartItemCreate, ShippingInfo
from app.crud import user, cart, shipping
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.schemas.order import OrderCreate, OrderItemCreate
from app.models.order import Order, OrderItem, OrderStatus
from sqlalchemy import func
from app.models.models import CartItem
from app.models.product import Product, ProductPricingTier
from pydantic import BaseModel
from typing import List, Optional
from collections import defaultdict

router = APIRouter()

# New schema for checkout with selected items
class CheckoutRequest(BaseModel):
    shipping_info: ShippingInfo
    cart_item_ids: Optional[List[int]] = None  # If None, checkout all items

@router.post("/cart/add")
def add_item(data: CartItemCreate, user_id: int, db: Session = Depends(get_db)):
    return cart.add_to_cart(db, user_id, data.product_id, data.quantity)

@router.get("/cart")
def get_cart_items(user_id: int, db: Session = Depends(get_db)):
    return cart.get_cart(db, user_id)

def get_price_for_quantity(product, quantity, db):
    """Get the appropriate price based on quantity from pricing tiers"""
    # Get all pricing tiers for the product, ordered by moq descending
    pricing_tiers = db.query(ProductPricingTier).filter(
        ProductPricingTier.product_id == product.id
    ).order_by(ProductPricingTier.moq.desc()).all()
    
    # Find the appropriate tier based on quantity
    for tier in pricing_tiers:
        if quantity >= tier.moq:
            return tier.price
    
    # If no tier matches, return the lowest tier price or 0
    if pricing_tiers:
        return pricing_tiers[-1].price
    return 0

@router.get("/cart/items")
def get_cart_items_for_checkout(user_id: int, db: Session = Depends(get_db)):
    """Get cart items with details for checkout selection"""
    cart_items = db.query(CartItem).filter(
        CartItem.user_id == user_id,
        CartItem.status == "in_cart"
    ).all()
    
    result = []
    for item in cart_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            price = get_price_for_quantity(product, item.quantity, db)
            result.append({
                "cart_item_id": item.id,
                "product_id": product.id,
                "product_name": product.name,
                "quantity": item.quantity,
                "price": price,
                "total_price": price * item.quantity,
                "vendor_id": product.vendor_id  # Include vendor_id in cart items response
            })
    
    return result

@router.post("/checkout")
def checkout(user_id: int, data: CheckoutRequest, db: Session = Depends(get_db)):
    # 1. Get cart items based on selection
    query = db.query(CartItem).filter(
        CartItem.user_id == user_id,
        CartItem.status == "in_cart"
    )
    
    # If specific items are selected, filter by those IDs
    if data.cart_item_ids:
        query = query.filter(CartItem.id.in_(data.cart_item_ids))
        
        # Validate that all requested items belong to the user
        requested_count = len(data.cart_item_ids)
        actual_count = query.count()
        if actual_count != requested_count:
            raise HTTPException(
                status_code=400, 
                detail="Some selected cart items are not valid or don't belong to you"
            )
    
    cart_items = query.all()

    if not cart_items:
        raise HTTPException(status_code=400, detail="No items selected for checkout")

    # 2. Group cart items by vendor
    vendor_items = defaultdict(list)
    for item in cart_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            # Get the correct price based on quantity from pricing tiers
            price = get_price_for_quantity(product, item.quantity, db)
            vendor_items[product.vendor_id].append({
                'cart_item': item,
                'product': product,
                'price': price
            })

    if not vendor_items:
        raise HTTPException(status_code=400, detail="No valid products found for checkout")

    # 3. Create separate orders for each vendor
    created_orders = []
    total_checkout_amount = 0
    total_items_count = 0
    
    for vendor_id, items in vendor_items.items():
        # Calculate total amount for this vendor
        vendor_total = 0
        for item_data in items:
            vendor_total += item_data['price'] * item_data['cart_item'].quantity
        
        # Create order for this vendor
        new_order = Order(
            customer_name=data.shipping_info.full_name,
            customer_email=data.shipping_info.email,
            customer_phone=data.shipping_info.phone,
            shipping_address=f"{data.shipping_info.address}, {data.shipping_info.city}, {data.shipping_info.state} - {data.shipping_info.pincode}",
            total_amount=vendor_total,
            vendor_id=vendor_id,
            status=OrderStatus.Pending
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        # Create OrderItems for this vendor's order
        vendor_items_count = 0
        for item_data in items:
            cart_item = item_data['cart_item']
            product = item_data['product']
            price = item_data['price']
            
            db.add(OrderItem(
                product_id=product.id,
                product_name=product.name,
                quantity=cart_item.quantity,
                price=price,
                vendor_id=vendor_id,
                order_id=new_order.id
            ))
            vendor_items_count += cart_item.quantity
        
        # Update cart item statuses for this vendor
        for item_data in items:
            item_data['cart_item'].status = "checkout"
        
        created_orders.append({
            "order_id": new_order.id,
            "vendor_id": vendor_id,
            "total_amount": vendor_total,
            "items_count": vendor_items_count
        })
        
        total_checkout_amount += vendor_total
        total_items_count += vendor_items_count

    db.commit()

    return {
        "message": "Orders placed successfully",
        "orders": created_orders,
        "total_amount": total_checkout_amount,
        "total_items_count": total_items_count,
        "orders_created": len(created_orders)
    }

# Alternative: Separate endpoint for partial checkout if you prefer
@router.post("/checkout/selected")
def checkout_selected_items(
    user_id: int, 
    cart_item_ids: List[int],
    shipping_info: ShippingInfo,
    db: Session = Depends(get_db)
):
    """Checkout specific cart items by their IDs"""
    return checkout(user_id, CheckoutRequest(
        shipping_info=shipping_info,
        cart_item_ids=cart_item_ids
    ), db)