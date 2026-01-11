from .models import Product, CartItem
from .coupon import calculate_item_discount
from .email_service import EmailService
from .cart import get_cart_item

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