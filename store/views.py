from django.shortcuts import render, get_object_or_404
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView, GenericAPIView, DestroyAPIView
from .serializers import ProductSerializer, CartSerializer, ClientSerializer, AddToCartSerializer, DeleteCartItemSerializer
from .models import Product, Cart, Client, CartItem
from rest_framework import viewsets
from rest_framework import permissions, status
from .pagination import ProductStorePagination
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from .services import authenticate_client


#==STORE==

class ProductsStoreView(ListAPIView):
    pagination_class = ProductStorePagination
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductSerializer    
    queryset = Product.objects.all()

class CartViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartSerializer
    queryset = Cart.objects.all()

    def get_queryset(self):
        queryset = Cart.objects.filter(user=self.request.user)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
class ProductDetail(RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductSerializer
    queryset = Product.objects.all()
    lookup_field = 'slug'

class AddToCart(APIView):
    permission_classes = [permissions.IsAuthenticated]
        
    def post(self, request, pk, *args, **kwargs,):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = Product.objects.get(id=pk)
        quantity = serializer.validated_data.get('product_quantity')

        cart, _= Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        cart_item.save()

        return Response({'detail': 'Product Added To Cart', 'cart_subtotal': cart_item.subtotal()}, status=status.HTTP_200_OK)

class DeleteCartItem(APIView):
    permission_classes =[permissions.IsAuthenticated]

    def delete(self, request, pk, *args, **kwargs):
        serializer = DeleteCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = Cart.objects.get(user=request.user)
        cart_item = cart.items.filter(product__id=pk).first()
        qtd_to_remove = serializer.validated_data.get('product_quantity')

        if cart_item:
            cart_item.quantity -= qtd_to_remove
            if cart_item.quantity <= 0:
                cart_item.delete()
                return Response({'detail': 'The product was completely removed from your cart', 'cart_subtotal': cart_item.subtotal()},status=status.HTTP_200_OK)
            else:
                cart_item.save()
                return Response({'detail': 'The product quantity has been updated in your cart', 'cart_subtotal': cart_item.subtotal()},status=status.HTTP_200_OK)
        
        return Response({"error": "The product doesn't exist in your cart"}, status=status.HTTP_404_NOT_FOUND)


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