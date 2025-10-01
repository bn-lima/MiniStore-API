from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token


def authenticate_client(username, password):
    user = authenticate(username=username, password=password)
    if user is not None:
        token, _ = Token.objects.get_or_create(user=user)

        return token