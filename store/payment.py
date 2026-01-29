from .coupon import get_discount, calculate_total_price
from .services import get_dict_items
from .models import MPPreference, MpPayment
import uuid
import hmac
import requests
import hashlib
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from datetime import timedelta
import mercadopago

def mp_create_preference(cart, full_name, cpf, email, request):
    discount = cart.coupon
    total_price, is_discount = calculate_total_price(cart, discount)

    sdk = mercadopago.SDK(settings.MERCADO_PAGO_KEY)

    request_options = mercadopago.config.RequestOptions()
    request_options.custom_headers = {
        'x-idempotency-key': str(uuid.uuid4())
    }

    items = get_dict_items(cart, request, discount)

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

        "additional_info": f"Discount: {discount.discount_percent}" if is_discount else "",

    }

    preference = sdk.preference().create(payment_data, request_options)
    result = preference["response"]
    
    mp_preference = MPPreference.objects.create(
        preference_expiration = expiration_to,
        value = total_price,
        preference_id = result['id'],
        init_point = result['sandbox_init_point'], #LINK DE PAGAMENTO SIMULADO 
        payer_email = email
    )

    cart.preference = mp_preference
    cart.save()

    return mp_preference

def create_payment(cart, payment_data):
    preference = cart.preference

    MpPayment.objects.create(
        user = cart.user,
        cart = cart,
        preference=preference,
        payment_id=payment_data['id'],
        amount=payment_data['transaction_amount'],
        payment_method=payment_data['payment_method_id'],
    )

    cart.passed_payment_step = True
    cart.save()

def get_pending_payment(user):
    payment = user.payments.filter(finalized=False).first()

    if not payment:
        return None, None
    return payment, payment.cart

def has_active_preference(cart):
    if not cart.preference:
        return None
    if cart.preference.expired:
        return None
    if cart.preference.finalized:
        return None
    
    return cart.preference
        


def finalize_preference(preference):
    preference.finalized = True

    preference.save()

def get_payment_data(data_id):
    url = f"https://api.mercadopago.com/v1/payments/{data_id}"

    response = requests.get(url, headers={"Authorization": f"Bearer {settings.MERCADO_PAGO_KEY}", "Content-Type": "application/json"})
    data = response.json()

    return data

def validate_signature(data_id, x_request_id, signature_header):

    ts = signature_header.split(",")[0].split("=")[1]
    received_signature = signature_header.split(",")[1].split("=")[1]

    payload = f"id={data_id};request-id={x_request_id};ts={ts}".encode()

    v1_calculated = hmac.new(settings.MERCADO_PAGO_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()

    valid_signature = hmac.compare_digest(v1_calculated, received_signature)

    if valid_signature:
        return True
    return False