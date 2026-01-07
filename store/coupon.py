from .models import DiscountCoupon
from .cart import get_cart_items_unit_price

def validate_and_apply_discount(discount, cart):
    total = cart.total()

    if not discount:
        return total, "Coupon does not exist", False

    if not discount.is_active():
        return total, "Coupon code is not active", False
    
    if not discount.verify_min_purchase(cart.total()):
        return total, "Minimum purchase amount not reached", False
    
    discounted_price = discount.apply_discount(total)

    return discounted_price, f"Coupon applied {discount.discount_percent}% off", True

def get_discount(coupon_code):
    try:
        discount = DiscountCoupon.objects.get(cupom=coupon_code)
    except DiscountCoupon.DoesNotExist:
        return None
    return discount

def calculate_total_price(cart, discount):

    total_price, _, discount_applied = validate_and_apply_discount(discount, cart)
    
    if discount_applied:
        is_discount = True
    else:
        is_discount = False
        total_price = cart.total()

    return total_price, is_discount

def calculate_item_discount(cart, coupon_code):
    discount = get_discount(coupon_code)
    _, _, discount_applied = validate_and_apply_discount(discount, cart)

    cart_item_subtotal = get_cart_items_unit_price(cart)

    if discount_applied:
        discount_percent = discount.discount_percent

        cart_item_discounted_price = []

        for item in cart.items.all():
            cart_item_discounted_price.append(item.subtotal() * (1 - discount_percent/100)/item.quantity)

        return cart_item_discounted_price
    return cart_item_subtotal

def add_coupon_to_cart(coupon_code, cart):
    discount = get_discount(coupon_code)

    _, _, applied = validate_and_apply_discount(discount, cart)
    if applied:
        cart.coupon = discount
        cart.save()
        return discount
    
    return None