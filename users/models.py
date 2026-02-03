from django.db import models
from django.contrib.auth.models import AbstractUser
from .validators import NUMERIC_VALIDATOR
from django.utils import timezone
import uuid
from datetime import timedelta

class Client(AbstractUser):
    
    cpf = models.CharField(max_length=11, validators=[NUMERIC_VALIDATOR], unique=True)
    location = models.CharField(max_length=200)
    phone = models.CharField(max_length=11, validators=[NUMERIC_VALIDATOR])
    email = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.username} - {self.email}"

def token_expiration():
    return timezone.now() + timedelta(hours=1)

class PasswordResetToken(models.Model):
    user = models.ForeignKey(Client, blank=False, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=token_expiration)
    used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def mark_as_used(self):
        self.used = True
        return self.used