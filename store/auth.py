from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
import uuid
from.models import PasswordResetToken
from django.core.mail import EmailMessage
    
def authenticate_client(username, password): 
    user = authenticate(username=username, password=password)
    if user is not None:
        token, _ = Token.objects.get_or_create(user=user)

        return token
    
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

def send_reset_email(token, user):
    link = f"http://127.0.0.1:8000/user/password_reset/?token={token.token}"
    
    email_message = EmailMessage(
        subject = "Password reset request",

        body = (f"We received a request to reset your password\n\n"
                f"To set a new password, click the link below:\n\n{link}\n\n"
                f"If you didn't request this change, please ignore this email."
                ),

        to = [user.email]
    )
    email_message.send()

