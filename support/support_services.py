from .models import SupportChannel

def get_support_channel(user):
    try:
        channel = SupportChannel.objects.get(user=user, active=True)
    except SupportChannel.DoesNotExist:
        return None
    return channel