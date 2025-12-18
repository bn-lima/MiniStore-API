from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from .models import DiscountCupom, MPPreference, Cart
from django.conf import settings
import uuid
import mercadopago
from django.utils import timezone
from datetime import timedelta
import requests
import hmac
import hashlib
from django.urls import reverse


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

def get_discount(coupon_code):
    try:
        discount = DiscountCupom.objects.get(cupom=coupon_code)
    except DiscountCupom.DoesNotExist:
        return None
    return discount

def get_cart_items_unit_price(cart):
    unit_pirce = []
    for item in cart.items.all():
        unit_pirce.append(item.product.price)
    return unit_pirce

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

        "notification_url": reverse('webhook'),  #request.build_absolute_uri(reverse('webhook')),

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
        cart = cart
    )

    return result

def create_payment(cart, payment_id):

    payment = get_payment_data(payment_id)
    payment_method = payment['payment_type_id']

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

def get_cart_by_id(cart_id):
    try:
        cart = Cart.objects.get(pk=cart_id)
    except Cart.DoesNotExist:
        return None
    return cart