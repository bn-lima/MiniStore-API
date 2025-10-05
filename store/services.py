from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from .models import PasswordResetToken
from rest_framework import status as drf_status
import uuid

def authenticate_client(username, password): 
    user = authenticate(username=username, password=password)
    if user is not None:
        token, _ = Token.objects.get_or_create(user=user)

        return token

def send_reset_email_simulation(token): #DEF PROVISÓRIA
    link = f"http://127.0.0.1:8000/user/password_reset/?token={token.token}" #SUBSTITUIR POR UM ENVIO DE EMAIL SIMULADO NO TERMINAL
    return link

def validate_password(password, confirm_password):
    if password != confirm_password:
        return False
    return True

def validate_reset_token(token_str):
    
    if not token_str:
        return None
    
    try:
        uuid_token = uuid.UUID(token_str)
    except ValueError:
        return None

    try:
        token = PasswordResetToken.objects.get(token=uuid_token)
    except PasswordResetToken.DoesNotExist:
        return None
    
    return token
            