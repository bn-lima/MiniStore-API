from django.db import models
from users.models import Client

class SupportMessage(models.Model):
    user = models.ForeignKey(Client, on_delete=models.CASCADE, blank=False, null=False)
    message = models.CharField(max_length=5000, blank=False)
    date = models.DateTimeField(auto_now=True)
    channel=models.ForeignKey('SupportChannel', on_delete=models.CASCADE, null=False, blank=False, related_name="messages")

    def __str__(self):
        return f"{self.user.username} - {self.date}"

class SupportChannel(models.Model):
    user = models.ForeignKey(Client, on_delete=models.CASCADE, null=False, blank=False)
    active = models.BooleanField(default=True)
    in_progress = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}"
