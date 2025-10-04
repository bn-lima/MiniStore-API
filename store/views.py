from django.shortcuts import render, get_object_or_404
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView, GenericAPIView
from .serializers import ProductSerializer, CartSerializer, ClientSerializer, ChangePasswordSerializer, PasswordResetRequestSerializer, PasswordResetSerializer
from .models import Product, Cart, Client, PasswordResetToken
from rest_framework import viewsets
from rest_framework import permissions, status
from .pagination import ProductStorePagination
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from .services import authenticate_client, send_reset_email_simulation
import uuid

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
        token = serializer.save()

        link = send_reset_email_simulation(token)
        return Response({'detail':'An email has been sent to you with a password reset link', 'link': link}, status=status.HTTP_200_OK)
    

class PasswordResetClient(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        token_str = request.query_params.get('token')
        if not token_str:
            return Response({'error': 'Token is required'},status=status.HTTP_400_BAD_REQUEST)
        
        try:
            uuid_token = uuid.UUID(token_str)
        except ValueError:
            return Response({'error': 'Invalid token'},status=status.HTTP_400_BAD_REQUEST)

        try:
            token = PasswordResetToken.objects.get(token=uuid_token)
        except PasswordResetToken.DoesNotExist:
            return Response({'error':'Token does not exist'},status=status.HTTP_404_NOT_FOUND)
               
        serializer = PasswordResetSerializer(data=request.data, context={'token':token})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Your password has been changed successfully'},status=status.HTTP_200_OK)