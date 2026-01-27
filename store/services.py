from .models import Product, CartItem
from .coupon import calculate_item_discount
from .email_service import EmailService
from .cart import get_cart_item
from django.db import transaction

def get_dict_items(cart, request, discount): 
    items = []
    item_price = calculate_item_discount(cart, discount)

    for item, price in zip(cart.items.all(), item_price):
            mp_item = {
                "id": item.id,
                "title": item.product.name,
                "description": item.product.description,
                "picture_url": request.build_absolute_uri(item.product.picture.url),
                "category_id": item.product.category,
                "quantity": item.quantity,
                "currency_id": "BRL",
                "unit_price": float(price),
            }

            items.append(mp_item)
    return items

def verify_order_status(status, email, order):
    send_email_message = EmailService(email, order)

    status_methods = {
        "pending":  send_email_message.order_created,
        "paid": send_email_message.paid_order, 
        "processing": send_email_message.processing_order,
        "shipped": send_email_message.order_shipped,
        "out_for_delivery": send_email_message.order_out_for_delivery,
        "delivered": send_email_message.order_delivered,
        "cancelled": send_email_message.order_cancelled, 
        "refunded": send_email_message.refunded_order
    }

    method = status_methods.get(status)
    if method:
        method()

def get_and_validate_product(pk):

    try:
        product = Product.objects.get(id=pk)
    except Product.DoesNotExist:
        return None 

    if not product.active:
        return None
    
    return product

    
def calculate_total_quantity(quantity_to_add, cart, product):
    cart_item = get_cart_item(cart, product)

    if not cart_item:
        items_quantity = 0
    else:
        items_quantity = cart_item.quantity

    total_quantity = items_quantity + quantity_to_add

    return total_quantity

def check_insufficient_stock(cart):
    for item in cart.items.all():
        product = item.product

        if product.stock < item.quantity and not item.is_reserved:
            return item, product, True
        
    return None, None, False

@transaction.atomic()
def decrease_reserved_stock(cart):
    for item in cart.items.all():
        product = item.product

        product.reserved_stock -= item.quantity

        product.save()

def reduce_cart_item(item, stock):
    if stock == 0:
        item.delete()
        return None
    
    item.quantity = stock
    item.save()

    return item.quantity

def is_item_inactive(cart):
    for item in cart.items.all():
        if not item.product.active and not item.is_reserved:
            item.delete()
            return True, item.product.name
    
    return False, None

@transaction.atomic()
def reserve_and_check_product_stock(cart):
    for item in cart.items.all():
        
        product = Product.objects.select_for_update().get(id=item.product.id)

        if product.stock < item.quantity:
            return False, product.name

        product.stock -= item.quantity

        if product.stock == 0:
            product.active = False

        product.reserved_stock += item.quantity
        item.is_reserved = True

        item.save()
        product.save()

    return True, None


def return_product_stock(cart):
    for item in cart.items.all():
        product = item.product

        product.stock += item.quantity
        
        product.active = True

        product.reserved_stock -= item.quantity
        item.is_reserved = False

        item.save()
        product.save()