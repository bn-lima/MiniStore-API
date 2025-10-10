from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from .models import DiscountCupom
from django.core.mail import EmailMessage

def authenticate_client(username, password):
    user = authenticate(username=username, password=password)
    if user is not None:
        token, _ = Token.objects.get_or_create(user=user)

        return token
    
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

def calculate_total_price(code, cart, discount):
    if discount and code:
        total_price, _ = validate_coupon(code, cart)
        if total_price == cart.total():
            discount = None
    else:
        total_price = cart.total()
        discount = None
        
    return total_price, discount

def verify_order_status(status, email, order):
    send_email_message = EmailService(email, order)

    status_methods = {
        "pending":  send_email_message.order_created,
        "paid": send_email_message.paid_order, 
        "processing": send_email_message.processing_order,
    }

    method = status_methods.get(status)
    if method:
        method()

        #DICT DE STATUS DO MODELO

#     status_method = {
#         "pending": "Pending",
#         "paid": "Paid", 
#         "processing": "Processing",
#         "shipped": "Shipped",
#         "out_for_delivery": "Out for delivery",
#         "delivered": "Delivered",
#         "cancelled": "Cancelled",
#         "refunded": "Refunded",
# }

class EmailService:
    def __init__(self, email, order):
        self.order_code = str(order.order_id)[:7]
        self.email = email
        
    def order_created(self):
        email_message = EmailMessage(
            subject = f"Your order #{self.order_code} has been created successfully!",
            body = f"Your order #{self.order_code} has been created. You'll be notified as soon as there are updates.",
            to = [self.email]
        )
        email_message.send()

    def processing_order(self):
        email_message = EmailMessage(
            subject = f"Your order #{self.order_code} is being processed!",
            body = f"We'd like to inform you that your order #{self.order_code} is being processed. As soon as there are updates, you'll be notified.",
            to = [self.email]
        )
        email_message.send()

    def paid_order(self):
        email_message = EmailMessage(
            subject = f"Your order payment has been approved!",
            body = f"We'd like to inform you that your payment has been approved! As soon as there are updates about your order #{self.order_code}, you'll be notified.",
            to = [self.email]
        )
        email_message.send()