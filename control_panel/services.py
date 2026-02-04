from support.models import SupportChannel

def is_channel_in_progress(channel, user):
    messages = channel.messages.filter(user=user)

    if not messages.exists():
        return False
    
    if messages.count() == 1:
        return True
    
    return False

def get_support_channel_by_id(id):
    try:
        channel = SupportChannel.objects.get(id=id, active=True)
    except SupportChannel.DoesNotExist:
        return None
    return channel