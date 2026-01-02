from .models import MPPreference, Product
from django.conf import settings
import uuid
import mercadopago
from django.utils import timezone
from datetime import timedelta
import requests
import hmac
import hashlib
from django.urls import reverse
from django.core.mail import EmailMessage
from .coupon import calculate_item_discount, get_discount, calculate_total_price

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

def mp_create_preference(cart, full_name, cpf, email, coupon_code, request):
    discount_obj = get_discount(coupon_code)
    total_price, discount = calculate_total_price(coupon_code, cart, discount_obj)

    sdk = mercadopago.SDK(settings.MERCADO_PAGO_KEY)

    request_options = mercadopago.config.RequestOptions()
    request_options.custom_headers = {
        'x-idempotency-key': str(uuid.uuid4())
    }

    items = get_dict_items(cart, request, coupon_code)

    expiration_from = timezone.now()
    expiration_to = timezone.now() + timedelta(minutes=60)

    payment_data = {
        "items": items,

        "payer": {
            "name": full_name,
            "email": email,
            "identification": {
                "type": "CPF",
                "number": cpf
            }
        },

        "back_urls": {
		"success": "http://127.0.0.1:8000/payment_status/success/",
		"failure": "http://127.0.0.1:8000/payment_status/failure/",
		"pending": "http://127.0.0.1:8000/payment_status/pending/",
        },

        #"auto_return": "approved", (O Mercado Pago não consegue retornar automaticamente para localhost)

        "notification_url": reverse('webhook'),  #request.build_absolute_uri(reverse('webhook')), (((PRA NAO DAR ERRO NO LOCALHOST))))

        "expires": True,
        "expiration_date_from": expiration_from.isoformat(),
        "expiration_date_to": expiration_to.isoformat(),

        "external_reference": str(cart.id),

        "statement_descriptor": "MiniStore",

        "additional_info": f"Discount: {discount.discount_percent}" if discount else "",

    }

    preference = sdk.preference().create(payment_data, request_options)
    result = preference["response"]
    
    MPPreference.objects.create(
        preference_expiration = expiration_to,
        value = total_price,
        preference_id = result['id'],
        init_point = result['init_point'],
        payer_email = email,
        cart = cart
    )

    return result

def create_payment(cart, payment_data):

    payment_method = payment_data['payment_type_id']

    preference = get_preference(cart)

    preference.payment_method = payment_method
    preference.save()

    cart.passed_payment_step = True
    cart.save()

def get_preference(cart):
    try:
        preference = MPPreference.objects.get(cart=cart, expired=False, paid=False)
    except MPPreference.DoesNotExist:
        return None

    if preference.is_preference_expired():
        return None
    
    return preference

def finalize_preference(preference):
    preference.expired = True
    preference.paid = True

    preference.save()

def validate_signature(data_id, x_request_id, signature_header):

    ts = signature_header.split(",")[0].split("=")[1]
    received_signature = signature_header.split(",")[1].split("=")[1]

    payload = f"id={data_id};request-id={x_request_id};ts={ts}".encode()

    v1_calculated = hmac.new(settings.MERCADO_PAGO_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()

    valid_signature = hmac.compare_digest(v1_calculated, received_signature)

    if valid_signature:
        return True
    return False

def get_payment_data(data_id):
    url = f"https://api.mercadopago.com/v1/payments/{data_id}"

    response = requests.get(url, headers={"Authorization": f"Bearer {settings.MERCADO_PAGO_KEY}", "Content-Type": "application/json"})
    data = response.json()

    return data

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

