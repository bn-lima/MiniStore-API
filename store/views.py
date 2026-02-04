from rest_framework.generics import ListAPIView, RetrieveAPIView
from .models import Product, Cart, Order
from .serializers import ProductSerializer, CartItemQuantitySerializer, OrderSerializer, AddToCartSerializer, DeleteCartItemSerializer, CartResponseSerializer, OrderUserListSerializer
from rest_framework import permissions, status
from .pagination import ProductStorePagination, OrderListPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from .services import get_and_validate_product
from .cart import get_cart_item
from payments.payment_services import get_pending_payment

#==STORE==

class ProductsStoreView(ListAPIView):
    pagination_class = ProductStorePagination
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductSerializer    
    queryset = Product.objects.all()

    def get_queryset(self):
        queryset = Product.objects.filter(active=True)
        return queryset
    
class ProductDetail(RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductSerializer
    queryset = Product.objects.all()
    lookup_field = 'slug'

class CartView(APIView):
    permission_classes = [permissions.AllowAny]
        
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

#==ORDER==
class OrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = OrderListPagination

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
    
    def get(self, request, *args, **kwargs):
        query = Order.objects.filter(user=request.user)

        pagination = self.pagination_class()
        page = pagination.paginate_queryset(query, request)

        serializer = OrderUserListSerializer(page, many=True)

        return pagination.get_paginated_response(serializer.data)

