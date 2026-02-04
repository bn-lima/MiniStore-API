from rest_framework import serializers
from .models import SupportMessage, SupportChannel

class SendSupportMessageSerializer(serializers.ModelSerializer):
    message = serializers.CharField(max_length=5000)
    
    class Meta:
        model = SupportMessage
        exclude = ('channel', 'user')

    def save(self, **kwargs):
        channel = self.context.get('channel')
        user = self.context.get('user')

        return SupportMessage.objects.create(
            channel=channel,
            user=user,
            message=self.validated_data.get('message')
        )
    
class ShowSupportMessagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportMessage
        exclude = ('channel',)

class SupportChannelSerializer(serializers.ModelSerializer):
    messages = ShowSupportMessagesSerializer(many=True, read_only=True)
    class Meta:
        model = SupportChannel
        fields = ('messages',)