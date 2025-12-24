from django.shortcuts import render, get_object_or_404
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView, GenericAPIView, DestroyAPIView
from .serializers import ProductSerializer, CartSerializer, ClientSerializer, CartItemQuantitySerializer, OrderSerializer, CouponCodeSerializer, UpdateStatusSerializer, UserOrdersListSerializer, PayerSerializer, CouponSerializer
from .models import Product, Cart, Client, CartItem, Order, DiscountCupom
from rest_framework import permissions, status
from .pagination import ProductStorePagination, OrderListPagination
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from .services import authenticate_client, mp_create_preference, create_payment, get_preference, validate_signature, get_cart_by_id, get_payment_data, get_webhook_headers

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

class AddToCart(APIView):
    permission_classes = [permissions.IsAuthenticated]
        
    def post(self, request, pk, *args, **kwargs,):
        serializer = CartItemQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = Product.objects.get(id=pk) #AJUSTAR ISSO PRA N DAR ERRO SE O PRODUTO N EXISTIR
        quantity = serializer.validated_data.get('product_quantity')

        cart, _= Cart.get_cart(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

        total_quantity = quantity if created else quantity + cart_item.quantity

        if not product.active:
            return Response({"error": "This product isn't active"}, status=status.HTTP_404_NOT_FOUND)
        if product.stock < total_quantity:
            return Response({"error": "The quantity to add exceeds available stock"},status=status.HTTP_400_BAD_REQUEST)
        
        cart_item.quantity = total_quantity
        cart_item.save()

        return Response({'detail': 'Product Added To Cart', 'cart_subtotal': cart_item.subtotal(), 'cart_total': cart.total(), 'total_items': cart.total_items()}, status=status.HTTP_200_OK)
    
class DeleteCartItem(APIView):
    permission_classes =[permissions.IsAuthenticated]

    def delete(self, request, pk, *args, **kwargs):
        serializer = CartItemQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart, _ = Cart.get_cart(user=request.user)
        if not cart:
            return Response({"error": "You don't have an active cart"},status=status.HTTP_404_NOT_FOUND)
        #VALIDAR SE O CARRINHO POSSUI ITENS==============================================================================================
        cart_item = cart.items.filter(product__id=pk, product__active=True).first()
        qtd_to_remove = serializer.validated_data.get('product_quantity')

        if cart_item:
            cart_item.quantity -= qtd_to_remove
            if cart_item.quantity <= 0:
                cart_item.delete()
                return Response({'detail':  'The product was completely removed from your cart', 'cart_total': cart.total()},status=status.HTTP_200_OK)
            else:
                cart_item.save()
                subtotal = cart_item.subtotal()
                return Response({'detail': 'The product quantity has been updated in your cart', 'cart_subtotal': subtotal, 'cart_total': cart.total(), 'total_items': cart.total_items()},status=status.HTTP_200_OK)
        
        return Response({"error": "The product doesn't exist in your cart"}, status=status.HTTP_404_NOT_FOUND)
    
#==PAYMENT==

class Continue_Payment(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        cart, _ = Cart.get_cart(user=request.user)

        query_serializer = CouponCodeSerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        coupon_code = query_serializer.validated_data.get('coupon_code')

        if not cart.items.exists():
            return Response({"error": "You don't have items in your cart"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CartSerializer(cart, context={'coupon_code': coupon_code})
        
        cart.passed_continue_to_payment = True
        cart.save()

        return Response(serializer.data)

class CreatePreference(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        cart, _ = Cart.get_cart(user=request.user)
        preference = get_preference(cart)

        if not cart.items.exists():
            return Response({"error": "You do not have any items in your cart"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not cart.passed_continue_to_payment:
            return Response({"error": "You haven't completed the 'continue to payment' step"}, status=status.HTTP_400_BAD_REQUEST)
        
        if cart.passed_payment_step:
            return Response({"error": "You have already paid for these items"}, status=status.HTTP_400_BAD_REQUEST)
        
        if preference:
            return Response({"error": "You already have a pending payment"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PayerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        client_full_name = serializer.validated_data.get("client_full_name")
        client_cpf = serializer.validated_data.get("client_cpf")
        client_email = serializer.validated_data.get("client_email")
        
        query_serializer = CouponCodeSerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
    
        coupon_code = query_serializer.validated_data.get("coupon_code")

        response = mp_create_preference(cart, client_full_name, client_cpf, client_email, coupon_code, request)

        return Response({"init_point": response['init_point'], "preference_id": response['id']}) #LINK DE PAGAMENTO REAL DO MERCADO PAGO

class PaymentStatus(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, payment_state, *args, **kwargs):
        cart, _ = Cart.get_cart(user=request.user)
        preference = get_preference(cart)

        if not preference:
            return Response({"error": "You do not have a pending payment to verify the status"}, status=status.HTTP_400_BAD_REQUEST)

        if payment_state == "success":
            return Response({"detail": "The payment was successful"}, status=status.HTTP_200_OK)
        
        if payment_state == "failure":
            return Response({"detail": "The payment has failed"}, status=status.HTTP_400_BAD_REQUEST)
        
        if payment_state == "pending":
            return Response({"detail": "The payment is still pending"}, status=status.HTTP_200_OK)

#==WEBHOOK==
class WebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data

        data_id = data['data']['id']
        x_request_id, signature_header = get_webhook_headers(request)

        if not data_id or not x_request_id or not signature_header:
            return Response(status=status.HTTP_200_OK)

        valid_signature = validate_signature(data_id, x_request_id, signature_header)

        if valid_signature:
            payment_data = get_payment_data(data_id)
            payment_approved = payment_data['status']

            if payment_approved == 'approved':
                cart_id = payment_data['external_reference']
                cart = get_cart_by_id(cart_id)

                if not cart or cart.passed_payment_step:
                    return Response(status=status.HTTP_200_OK)
                
                create_payment(cart, payment_data)
                return Response(status=status.HTTP_200_OK)
            
        return Response(status=status.HTTP_200_OK)

#==ORDER==

class CreateOrder(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        cart, _ = Cart.get_cart(user=request.user)
        preference = get_preference(cart)

        if not cart.items.exists():
            return Response({"error": "You don't have items in your cart"}, status=status.HTTP_404_NOT_FOUND)
        
        if not cart.passed_payment_step:
            return Response({"error": "You must complete the payment before creating an order"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = OrderSerializer(
            data=request.data,
            context={
                'request': request,
                'coupon_code': request.data.get('coupon_code'),
                'cart': cart,
                'preference': preference
            })
        serializer.is_valid(raise_exception=True)

        order = serializer.save()

        return Response(OrderSerializer(order, context=serializer.context).data, status=status.HTTP_201_CREATED)
        
class UserOrdersList(ListAPIView):
    serializer_class = UserOrdersListSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Order.objects.all()
    pagination_class = OrderListPagination

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

class UpdateOrderStatus(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk, *args, **kwargs):
        order = get_object_or_404(Order, pk=pk)

        serializer = UpdateStatusSerializer(data=request.data, context={'order': order})
        serializer.is_valid(raise_exception=True)

        serializer.save()
        return Response({'status': order.status, 'detail': f'The order status was changed for {order.status}'})
    
#==AUTHENTICATION==
#ADICIONAR UMA VIEW PARA TROCAR A SENHA DPS
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

        username = request.data.get('username')
        password = request.data.get('password')

        token = authenticate_client(username, password)

        if token:
            return Response({'Token': token.key})
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
#ADMIN-PANEL

class ProductPanel(ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = ProductSerializer
    queryset = Product.objects.all()

class CouponPanel(ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = CouponSerializer
    queryset = DiscountCupom.objects.all()