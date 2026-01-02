from .models import CartItem, Cart

def get_cart_items_unit_price(cart):
    unit_price = []
    for item in cart.items.all():
        unit_price.append(item.product.price)
    return unit_price

def get_cart_item_by_id(cart, cart_item_id):
    try:
        cart_item = cart.items.get(product__id=cart_item_id)
    except CartItem.DoesNotExist:
        return None                                                   
    
    return cart_item

def get_cart_by_id(cart_id):
    try:
        cart = Cart.objects.get(pk=cart_id)
    except Cart.DoesNotExist:
        return None
    return cart

def update_cart_item_quantity(cart_item, total_quantity):
    cart_item.quantity = total_quantity
    cart_item.save()

def is_quantity_exceeding_stock(product, total_quantity, cart_item):
    if product.stock == 0:
        cart_item.delete()
        return True

    if product.stock < total_quantity:
        return True
    
    return False

def verify_cart_item_quantity(cart_item, quantity):
    cart_item.quantity -= quantity

    if cart_item.quantity <= 0:
        cart_item.delete()
        return False, None
    else: 
        cart_item.save()
        return True, cart_item.subtotal()