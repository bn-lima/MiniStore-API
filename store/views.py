from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView
from .models import Product, Cart, Client, Order, DiscountCoupon, SupportChannel
from .serializers import ProductSerializer, ContinueToPaymentResponseSerializer, ClientSerializer, CartItemQuantitySerializer, OrderSerializer, CouponCodeSerializer, UpdateStatusSerializer, UserOrdersListSerializer, ChangePasswordSerializer, PasswordResetRequestSerializer, PasswordResetSerializer, AddToCartSerializer, DeleteCartItemSerializer, PayerSerializer, CouponSerializer, CartItemResponseSerializer, CartResponseSerializer, PreferenceResponseSerializer, LoginSerializer, OrderUserListSerializer, SupportChannelSerializer, SendSupportMessageSerializer, SupportRequestsSerializer, AdminSendSupportMessageSerializer
from rest_framework import permissions, status
from .pagination import ProductStorePagination, OrderListPagination
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from .services import get_and_validate_product, decrease_reserved_stock, reduce_cart_item, check_insufficient_stock, is_item_inactive, reserve_and_check_product_stock, get_support_channel, get_support_channel_by_id
from .auth import validate_reset_token, send_reset_email
from .cart import get_cart_by_id, get_cart_item, proceed_to_payment
from .payment import mp_create_preference, create_payment, validate_signature, get_payment_data, finalize_preference, has_active_preference, get_pending_payment
from .utils import get_webhook_headers
from .coupon import add_coupon_to_cart, get_discount

# UTILIZAR SERIALIZERS NAS RESPOSTAS DA API

#==STORE==

class ProductsStoreView(ListAPIView):
    pagination_class = ProductStorePagination
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductSerializer    
    queryset = Product.objects.all()

    def get_queryset(self):
        queryset = Product.objects.filter(active=True)
        return queryset
    
class ProductDetail(RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductSerializer
    queryset = Product.objects.all()
    lookup_field = 'slug'

class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]
        
    def post(self, request, pk, *args, **kwargs,):
        cart, _= Cart.get_cart(user=request.user)

        quantity_serializer = CartItemQuantitySerializer(data=request.data)
        quantity_serializer.is_valid(raise_exception=True)

        product = get_and_validate_product(pk)

        if not product:
            return Response({"detail": "The product doesn't exist or isn't active"}, status=status.HTTP_404_NOT_FOUND)
        
        quantity = quantity_serializer.validated_data.get('product_quantity') 

        add_to_cart_serializer = AddToCartSerializer(data={}, context={"quantity": quantity, "cart": cart, "product": product})
        add_to_cart_serializer.is_valid(raise_exception=True)

        add_to_cart_serializer.save()

        cart_response = CartResponseSerializer(cart)

        return Response({'detail': 'Product Added To Cart', 'cart': cart_response.data}, status=status.HTTP_200_OK)
    

    def delete(self, request, pk, *args, **kwargs):
        cart, _ = Cart.get_cart(user=request.user)
        product = get_and_validate_product(pk)

        if not cart.items.exists():
            return Response({"detail": "Your cart is empty"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not product:
            return Response({"error": "The product doesn't exist or isn't active"},status=status.HTTP_400_BAD_REQUEST)
        
        quantity_serializer = CartItemQuantitySerializer(data=request.data)
        quantity_serializer.is_valid(raise_exception=True)

        cart_item = get_cart_item(cart, product)
            
        quantity = quantity_serializer.validated_data.get('product_quantity')

        serializer = DeleteCartItemSerializer(data={}, context={'quantity':quantity, 'cart_item': cart_item})
        serializer.is_valid(raise_exception=True)
        cart_item = serializer.save()

        cart_response = CartResponseSerializer(cart)

        if not cart_item:

            return Response({'detail':  'The product was completely removed from your cart', 'cart':cart_response.data},status=status.HTTP_200_OK)
        
        return Response({'detail': 'The product quantity has been updated in your cart', 'cart': cart_response.data},status=status.HTTP_200_OK)
 
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

#==ORDER==

class OrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        payment, cart = get_pending_payment(request.user)
        
        if not payment:
            return Response({"detail": "You do not have a pending payment"}, status=status.HTTP_400_BAD_REQUEST)

        if not cart.items.exists():
            return Response({"detail": "You don't have items in your cart"}, status=status.HTTP_400_BAD_REQUEST)

        if not cart.passed_payment_step:
            return Response({"detail": "You must complete the payment before creating an order"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = OrderSerializer(
            data={},
            context={
                'user': request.user,
                'cart': cart,
                'payment': payment
            })
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self, request, *args, **kwargs): # ADICIONAR PAGINAÇÃO AQUI
        query = Order.objects.filter(user=request.user)
        serializer = OrderUserListSerializer(query, many=True)

        return Response(serializer.data)
    
#==AUTHENTICATION==

class RegisterClient(CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ClientSerializer
    queryset = Client.objects.all()

class LogoutClient(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        Token.objects.filter(user=request.user).delete()
        return Response({'detail': 'Logout was successful'}, status=status.HTTP_204_NO_CONTENT)
    

class LoginClient(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):

        serializer = LoginSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data.get('token')

        if token:
            return Response({'Token': token.key})
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
#CONTROL-PANEL

class ProductPanel(ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = ProductSerializer
    queryset = Product.objects.all()

class CouponPanel(ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = CouponSerializer
    queryset = DiscountCoupon.objects.all()

class UpdateOrderStatus(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk, *args, **kwargs):
        order = get_object_or_404(Order, pk=pk)

        serializer = UpdateStatusSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        order = serializer.save()
        return Response({"detail": f"The order status has been updated to {order.status}"}, status=status.HTTP_200_OK)
    
class SupportRequests(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, *args, **kwargs):
        query = SupportChannel.objects.filter(active=True)

        if not query:
            return Response({"detail": "There are no active support channels"}, status=status.HTTP_404_NOT_FOUND)

        serializer = SupportRequestsSerializer(query, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, pk, *args, **kwargws):
        channel = get_support_channel_by_id(pk)

        if not channel:
            return Response({"detail": "Channel not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AdminSendSupportMessageSerializer(data=request.data, context={'user': request.user, 'channel': channel})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = SupportChannelSerializer(channel)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

#AUTH-PASSWORD MANAGEMENT

class ChangePasswordClient(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        user = request.user
        serializer = ChangePasswordSerializer(data=request.data, context = {'user': user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Your password was changed successfully'}, status=status.HTTP_200_OK)

class PasswordResetRequestClient(APIView):
    permission_classes = [permissions.AllowAny] 

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)   
        token, user = serializer.save()

        send_reset_email(token, user)
        return Response({'detail':'An email has been sent to you with a password reset link'}, status=status.HTTP_200_OK)
    

class PasswordResetClient(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        token_str = request.query_params.get('token')

        token = validate_reset_token(token_str)

        if not token:
            return Response({'error': 'Invalid or missing token'},status=status.HTTP_400_BAD_REQUEST)
        
        serializer = PasswordResetSerializer(data=request.data, context={'token':token})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Your password has been changed successfully'},status=status.HTTP_200_OK)

# SUPPORT

class RequestSupport(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        channel, _ = SupportChannel.objects.get_or_create(active=True, user=request.user)
        serializer = SupportChannelSerializer(channel)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class SendSupportMessage(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        channel = get_support_channel(request.user)

        if not channel:
            return Response({"detail": "You do not have an active support channel"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = SendSupportMessageSerializer(data=request.data, context={"channel":channel, "user":request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = SupportChannelSerializer(channel)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)