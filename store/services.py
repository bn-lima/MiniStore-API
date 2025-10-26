from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from .models import DiscountCupom, PasswordResetToken, Product, CartItem
from django.core.mail import EmailMessage
import uuid

def authenticate_client(username, password): 
    user = authenticate(username=username, password=password)
    if user is not None:
        token, _ = Token.objects.get_or_create(user=user)

        return token
    
def validate_coupon(coupon_code, cart):
    try:
        discount = DiscountCupom.objects.get(cupom=coupon_code)
    except DiscountCupom.DoesNotExist:
        return cart.total(), "Coupon code doesn't exist"
 
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

def send_reset_email(token, user):
    link = f"http://127.0.0.1:8000/user/password_reset/?token={token.token}"
    
    email_message = EmailMessage(
        subject = "Password reset request",

        body = (f"We received a request to reset your password\n\n"
                f"To set a new password, click the link below:\n\n{link}\n\n"
                f"If you didn't request this change, please ignore this email."
                ),

        to = [user.email]
    )
    email_message.send()

def validate_password(password, confirm_password):
    if password != confirm_password:
        return False
    return True

def validate_reset_token(token_str):
    
    if not token_str:
        return None
    
    try:
        uuid_token = uuid.UUID(token_str)
    except ValueError:
        return None

    try:
        token = PasswordResetToken.objects.get(token=uuid_token)
    except PasswordResetToken.DoesNotExist:
        return None
    
    return token

def validate_product(pk):

    try:
        product = Product.objects.get(id=pk)
    except Product.DoesNotExist:
        return None 

    if not product.active:
        return None
    
    return product

def get_cart_item(cart, product):
    try:
        cart_item = CartItem.objects.get(cart=cart, product=product)
        
    except CartItem.DoesNotExist:
        return None
    else:
        return cart_item
    
def calculate_total_quantity(quantity_to_add, cart, product):
    cart_item = get_cart_item(cart, product)

    if not cart_item:
        items_quantity = 0
    else:
        items_quantity = cart_item.quantity

    total_quantity = items_quantity + quantity_to_add

    return total_quantity

def get_cart_item_by_id(pk, cart):
    try:
        cart_item = CartItem.objects.get(product_id=pk, cart=cart)
    except CartItem.DoesNotExist:
        return None
    return cart_item

def product_is_inactive(cart):
    has_inactive = False
    inactive_list = []

    for item in cart.items.all():
        if not item.product.active:
            inactive_list.append(item.product.name)
            item.delete()
            has_inactive = True
            
    return has_inactive, inactive_list

def check_inactive_products(cart):
    has_inactive = False
    inactive_list = []

    for item in cart.items.all():
        if not item.product.active:
            inactive_list.append(item.product.name)
            has_inactive = True
    
    return has_inactive, inactive_list

def adjust_quantity_to_stock(cart):
    not_enough_stock = False
    high_quantity_items = []

    for item in cart.items.all():

        if item.quantity > item.product.stock:
            item.quantity = item.product.stock
            item.save()
            not_enough_stock = True
            high_quantity_items.append(item.product.name)

    return not_enough_stock, high_quantity_items

def check_quantity_to_stock(cart):
    exceeds_stock = False
    overstock_items = []

    for item in cart.items.all():
        if item.quantity > item.product.stock:
            exceeds_stock = True
            overstock_items.append(item.product.name)

    return exceeds_stock, overstock_items

def finalize_order_process(cart):
    for item in cart.items.all():
        product = item.product

        product.stock -= item.quantity

        if product.stock <= 0:
            product.stock = 0
            product.active = False
            
        product.save()
        
    cart.finalized = True
    cart.save()
