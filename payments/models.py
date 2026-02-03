from django.db import models
from django.utils import timezone
from users.models import Client

class MPPreference(models.Model):

    preference_expiration = models.DateTimeField(editable=False)
    expired = models.BooleanField(default=False, editable=False)
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    preference_id = models.CharField(max_length=200, null=True, blank=True, editable=False)
    init_point = models.URLField(max_length=500, null=True, blank=True, editable=False)
    payer_email = models.EmailField(null=True, blank=True, editable=False)

    finalized = models.BooleanField(default=False)

    def is_preference_expired(self):
        if timezone.now() >=     self.preference_expiration:
            self.expired = True
            self.save()
            return True
        return False

class MpPayment(models.Model):
    user = models.ForeignKey(Client, on_delete=models.CASCADE, blank=False, related_name='payments')
    cart = models.ForeignKey('store.Cart', on_delete=models.CASCADE, blank=False, null=False)
    payment_id = models.CharField(max_length=200, null=True, blank=True, unique=True)
    preference = models.ForeignKey(MPPreference, on_delete=models.CASCADE, blank=False, null=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=200, null=True, blank=True)

    finalized = models.BooleanField(default=False)