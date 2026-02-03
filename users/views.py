from rest_framework import permissions, status
from rest_framework.generics import CreateAPIView
from users.models import Client
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import LoginSerializer, ChangePasswordSerializer, PasswordResetRequestSerializer, PasswordResetSerializer, ClientSerializer
from .auth_services import validate_reset_token, send_reset_email
from rest_framework.authtoken.models import Token

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
