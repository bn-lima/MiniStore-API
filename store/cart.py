from .models import CartItem, Cart

def get_cart_items_unit_price(cart):
    unit_price = []
    for item in cart.items.all():
        unit_price.append(item.product.price)
    return unit_price

def get_cart_by_id(cart_id):
    try:
        cart = Cart.objects.get(pk=cart_id)
    except Cart.DoesNotExist:
        return None
    return cart

def get_cart_item(cart, product):
    try:
        cart_item = CartItem.objects.get(cart=cart, product=product)
        
    except CartItem.DoesNotExist:
        return None

    return cart_item

def proceed_to_payment(cart):
    cart.passed_continue_to_payment = True
    cart.save()