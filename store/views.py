from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView
from .serializers import ProductSerializer, CartSerializer, ClientSerializer, CartItemQuantitySerializer, OrderSerializer, CouponCodeSerializer, UpdateStatusSerializer, UserOrdersListSerializer, ChangePasswordSerializer, PasswordResetRequestSerializer, PasswordResetSerializer, AddToCartSerializer
from .models import Product, Cart, Client, CartItem, Order
from rest_framework import permissions, status
from .pagination import ProductStorePagination, OrderListPagination
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from .services import authenticate_client, send_reset_email, validate_reset_token, validate_product


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
        quantity_serializer = CartItemQuantitySerializer(data=request.data)
        quantity_serializer.is_valid(raise_exception=True)

        product = validate_product(pk)
        
        if not product:
            return Response({"error": "The product doesn't exist or isn't active"},status=status.HTTP_400_BAD_REQUEST)

        quantity = quantity_serializer.validated_data.get('product_quantity')
        cart, _= Cart.get_cart(user=request.user)

        serializer = AddToCartSerializer(data={}, context={'quantity':quantity, 'cart':cart, 'product': product})
        serializer.is_valid(raise_exception=True)
        cart_item = serializer.save()

        return Response({'detail': 'Product Added To Cart', 'cart_subtotal': cart_item.subtotal(), 'cart_total': cart.total(), 'total_items': cart.total_items()}, status=status.HTTP_200_OK)
    
class DeleteCartItem(APIView): # Mover essa lógica para o serializer ou services
    permission_classes =[permissions.IsAuthenticated]

    def delete(self, request, pk, *args, **kwargs):
        serializer = CartItemQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart, _ = Cart.get_cart(user=request.user)
        if not cart:
            return Response({"error": "You don't have an active cart"},status=status.HTTP_404_NOT_FOUND)
        
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
        return Response(serializer.data)
    
#==ORDER==

class CreateOrder(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):

        cart, _ = Cart.get_cart(user=request.user)

        if not cart.items.exists():
            return Response({"error": "You don't have items in your cart"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = OrderSerializer(
            data=request.data,
            context={
                'request': request,
                'coupon_code': request.data.get('coupon_code'),
                'cart': cart
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
        return Response({'status': order.status, 'detail': f"The order status was changed to {order.status} and an email was sent to order's owner"})
    
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

        username = request.data.get('username')
        password = request.data.get('password')

        token = authenticate_client(username, password)

        if token:
            return Response({'Token': token.key})
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
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