from rest_framework import serializers
from support.models import SupportChannel, SupportMessage
from .services import is_channel_in_progress
from store.models import DiscountCoupon, Order
from store.services import verify_order_status
from store.constants import OrderStatus

class SupportRequestsSerializer(serializers.ModelSerializer):

    class Meta:
        model = SupportChannel
        fields = '__all__'

class AdminSendSupportMessageSerializer(serializers.ModelSerializer):
    message = serializers.CharField(max_length=5000)
    desactive_chat = serializers.BooleanField(default=False)
    
    class Meta:
        model = SupportMessage
        exclude = ('channel', 'user')

    def save(self, **kwargs):
        channel = self.context.get('channel')
        user = self.context.get('user')

        if self.validated_data.get('desactive_chat'):
            channel.active = False
            channel.in_progress = False
            channel.save()

            self.validated_data['message'] = 'This chat has been closed. You can open another one at any moment.'

        message = SupportMessage.objects.create(
            channel=channel,
            user=user,
            message=self.validated_data.get('message')
        )

        if is_channel_in_progress(channel, user) and channel.active:
            channel.in_progress = True
            channel.save()

        return message
    
class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountCoupon
        fields = '__all__'

class UpdateStatusSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=OrderStatus.choices())

    class Meta:
        model = Order
        fields = ('status',)
    
    def save(self, **kwargs):
        order = self.instance
        order.status = self.validated_data.get('status')
        order.save()

        verify_order_status(order.status, order.user.email, order)
        
        return order
    
class OrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'