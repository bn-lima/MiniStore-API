from .models import Product
from django.core.mail import EmailMessage
from .coupon import calculate_item_discount

def get_dict_items(cart, request, coupon_code): 
    items = []
    item_price = calculate_item_discount(cart, coupon_code)

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

def get_webhook_headers(request):
    try:
        x_request_id = request.headers['x-request-id']
    except KeyError:
        x_request_id = None

    try:
        signature_header = request.headers['x-signature']
    except KeyError:
        signature_header = None

    return x_request_id, signature_header

def get_product_by_id(product_id):
    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return None
    return product

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

class EmailService:
    def __init__(self, email, order):
        self.order_code = str(order.order_id)[:7]
        self.email = email
        
    def order_created(self):
        email_message = EmailMessage(
            subject = f"Your order #{self.order_code} has been created successfully!",
            body = f"Your order #{self.order_code} has been created. You'll be notified as soon as there are any updates.",
            to = [self.email]
        )
        email_message.send()

    def processing_order(self):
        email_message = EmailMessage(
            subject = f"Your order #{self.order_code} is being processed!",
            body = f"We'd like to inform you that your order #{self.order_code} is being processed. You'll be notified as soon as there are any updates.",
            to = [self.email]
        )
        email_message.send()

    def paid_order(self):
        email_message = EmailMessage(
            subject = f"The payment for your order #{self.order_code} has been approved!",
            body = f"We'd like to inform you that your payment has been approved! As soon as there are updates regarding your order #{self.order_code}, you'll be notified.",
            to = [self.email]
        )
        email_message.send()

    def order_shipped(self):
        email_message = EmailMessage(
            subject = f"Your order #{self.order_code} has been shipped!",
            body = f"We'd like to inform you that your order #{self.order_code} has been shipped. You'll receive further updates about your order.",
            to = [self.email]
        )
        email_message.send()

    def order_out_for_delivery(self):
        email_message = EmailMessage(
            subject = f"Your order #{self.order_code} has left for delivery!",
            body = f"We'd like to inform you that your order #{self.order_code} has left for delivery. It will arrive at your residence soon.",
            to = [self.email]
        )
        email_message.send()

    def order_delivered(self):
        email_message = EmailMessage(
            subject = f"Your order #{self.order_code} has been delivered successfully!",
            body = f"Your order #{self.order_code} has been delivered successfully. Thank you for trusting us. Enjoy your product!",
            to = [self.email]
        )
        email_message.send()
    
    def order_cancelled(self):
        email_message = EmailMessage(
            subject = f'Your order #{self.order_code} has been cancelled successfully!',
            body = f"We'd like to inform you that your order has been cancelled successfully. You'll be notified if any further action is required.",
            to = [self.email]
        )
        email_message.send()

    def refunded_order(self):
        email_message = EmailMessage(
            subject = f"Your order #{self.order_code} has been refunded successfully!",
            body = f"We'd like to inform you that your order #{self.order_code} has been refunded successfully.",
            to = [self.email    ]
        )
        email_message.send()


def send_payment_aproved_email(email, order):
    order_code = str(order.order_id)[:7]

    email_message = EmailMessage(
        subject = f"The payment for your order #{order_code} has been approved!",
        body = f"We'd like to inform you that your payment has been approved! As soon as there are updates regarding your order #{order_code}, you'll be notified.",
        to = [email]
    )
    email_message.send()

