from .models import DiscountCupom
from .cart import get_cart_items_unit_price

#DAR UMA ARRUMADA NESSAS DEFS DPS

def validate_coupon(cupom_code, cart):
    try:
        discount = DiscountCupom.objects.get(cupom=cupom_code)
    except DiscountCupom.DoesNotExist:
        return cart.total(), "Coupon code does not exist"

    if not discount.is_active():
        return cart.total(), "Coupon code is not active"
    
    if not discount.verify_min_purchase(cart.total()):
        return cart.total(), "Minimum purchase amount not reached"
    
    discounted_price = discount.apply_discount(cart.total())

    return discounted_price, f"Coupon applied {discount.discount_percent}% off"

def get_discount(coupon_code):
    try:
        discount = DiscountCupom.objects.get(cupom=coupon_code)
    except DiscountCupom.DoesNotExist:
        return None
    return discount

def calculate_total_price(code, cart, discount):
    if discount and code:
        total_price, _ = validate_coupon(code, cart)
        if total_price == cart.total():
            discount = None
    else:
        total_price = cart.total()
        discount = None
        
    return total_price, discount

def calculate_item_discount(cart, coupon_code):
    discount_obj = get_discount(coupon_code)
    _, discount = calculate_total_price(coupon_code, cart, discount_obj)

    cart_item_subtotal = get_cart_items_unit_price(cart)

    if discount:
        discount_percent = discount.discount_percent

        cart_item_discounted_price = []

        for item in cart.items.all():
            cart_item_discounted_price.append(item.subtotal() * (1 - discount_percent/100)/item.quantity)

        return cart_item_discounted_price
    return cart_item_subtotal