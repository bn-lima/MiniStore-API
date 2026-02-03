from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from store.coupon import get_discount
from store.cart import get_cart_by_id
from store.services import is_item_inactive, check_insufficient_stock, reduce_cart_item, reserve_and_check_product_stock, decrease_reserved_stock
from store.models import Cart
from store.serializers import CouponCodeSerializer
from .payment_services import mp_create_preference, has_active_preference, proceed_to_payment, validate_signature, get_payment_data, create_payment, finalize_preference
from store.coupon import add_coupon_to_cart
from .serializers import ContinueToPaymentResponseSerializer, PreferenceResponseSerializer, PayerSerializer
from store.utils import get_webhook_headers


#==PAYMENT==

class ContinueToPayment(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        cart, _ = Cart.get_cart(user=request.user)

        if not cart.items.exists():
            return Response({"detail": "You don't have items in your cart"}, status=status.HTTP_400_BAD_REQUEST)
        
        inactive, product_name = is_item_inactive(cart)

        if inactive:
            return Response({'detail': f'The item {product_name} is inactive and has been removed from your cart'}, status=status.HTTP_400_BAD_REQUEST)
        
        item, product, invalid_stock = check_insufficient_stock(cart)

        if invalid_stock:
            new_quantity = reduce_cart_item(item, product.stock)

            if not new_quantity:
                return Response({'detail': f'The item {product.name} is out of stock and has been removed from your cart.'},status=status.HTTP_400_BAD_REQUEST)
            
            return Response({'detail': f'Not enough stock for {item.product.name}. We have reduced the quantity for this item', 'new_quantity': new_quantity},status=status.HTTP_400_BAD_REQUEST)

        coupon_serializer = CouponCodeSerializer(data=request.data)
        coupon_serializer.is_valid(raise_exception=True)

        coupon_code = coupon_serializer.validated_data.get('coupon_code')

        response_serializer = ContinueToPaymentResponseSerializer({'cart':cart, 'coupon': get_discount(coupon_code)}, context={'cart':cart, 'coupon_code': coupon_code})
            
        add_coupon_to_cart(coupon_code, cart)
        proceed_to_payment(cart)

        return Response(response_serializer.data, status=status.HTTP_200_OK)

class CreatePreference(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        cart, _ = Cart.get_cart(user=request.user)
        preference = has_active_preference(cart)

        if not cart.items.exists():
            return Response({"detail": "You do not have any items in your cart"}, status=status.HTTP_400_BAD_REQUEST)
        
        inactive, product_name = is_item_inactive(cart)

        if inactive:
            return Response({'detail': f'The item {product_name} is inactive and has been removed from your cart'}, status=status.HTTP_400_BAD_REQUEST)

        item, product, invalid_stock = check_insufficient_stock(cart)

        if invalid_stock:
            new_quantity = reduce_cart_item(item, product.stock)

            if not new_quantity:
                return Response({'detail': f'The item {item.product.name} is out of stock and has been removed from your cart.'}, status=status.HTTP_400_BAD_REQUEST)

            return Response({'detail': f'Not enough stock for {item.product.name}. We have reduced the quantity for this item', 'new_quantity': new_quantity}, status=status.HTTP_400_BAD_REQUEST)
        
        if not cart.passed_continue_to_payment:
            return Response({"detail": "You haven't completed the 'continue to payment' step"}, status=status.HTTP_400_BAD_REQUEST)
        
        if cart.passed_payment_step:
            return Response({"detail": "You have already paid for these items"}, status=status.HTTP_400_BAD_REQUEST)
        
        if preference:
            response = PreferenceResponseSerializer(preference)
            return Response({"detail": "You already have a pending payment", 'preference': response.data}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PayerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        valid_reservation, product_name = reserve_and_check_product_stock(cart)

        if not valid_reservation:
            return Response({"Detail": f"Not enough stock for {item.product.name}"}, status=status.HTTP_400_BAD_REQUEST )

        client_full_name = serializer.validated_data.get("client_full_name")
        client_cpf = serializer.validated_data.get("client_cpf")
        client_email = serializer.validated_data.get("client_email")

        preference = mp_create_preference(cart, client_full_name, client_cpf, client_email, request)
    
        response = PreferenceResponseSerializer(preference)
        return Response(response.data, status=status.HTTP_200_OK) #LINK DE TESTE DO MERCADO PAGO

class PaymentStatus(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, state, *args, **kwargs):
        cart, _ = Cart.get_cart(user=request.user)  
        preference = cart.preference

        if not preference:
            return Response({"detail": "You do not have a pending preference to verify the status"}, status=status.HTTP_400_BAD_REQUEST)

        if state not in ["success", "failure", "pending"]:
            return Response({"detail": "Invalid payment status"}, status=status.HTTP_400_BAD_REQUEST)

        if state == "success":
            return Response({"detail": "The payment was successful"}, status=status.HTTP_200_OK)
        
        if state == "failure":
            return Response({"detail": "The payment has failed"}, status=status.HTTP_400_BAD_REQUEST)
        
        if state == "pending":
            return Response({"detail": "The payment is still pending"}, status=status.HTTP_200_OK)


#==WEBHOOK==
class WebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data

        data_id = data.get('data', {}).get('id')
        x_request_id, signature_header = get_webhook_headers(request)

        if not data_id or not x_request_id or not signature_header:
            return Response(status=status.HTTP_200_OK)

        valid_signature = validate_signature(data_id, x_request_id, signature_header)

        if valid_signature:
            payment_data = get_payment_data(data_id)
            payment_status = payment_data['status']

            if payment_status == 'approved':
                cart_id = payment_data['external_reference']
                cart = get_cart_by_id(int(cart_id))

                if not cart or cart.passed_payment_step:
                    return Response(status=status.HTTP_200_OK)
                
                create_payment(cart, payment_data)
                finalize_preference(cart.preference)
                decrease_reserved_stock(cart)
                return Response(status=status.HTTP_200_OK)
            
        return Response(status=status.HTTP_200_OK)