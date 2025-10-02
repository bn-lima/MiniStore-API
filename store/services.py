from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token


def authenticate_client(username, password):
    user = authenticate(username=username, password=password)
    if user is not None:
        token, _ = Token.objects.get_or_create(user=user)

        return token
    
def send_reset_email_simulation(token): #DEF PROVISÓRIA
    link = f"http://127.0.0.1:8000/future_url{token.token}" #SUBSTITUIR POR UM ENVIO DE EMAIL SIMULADO NO TERMINAL
    return link