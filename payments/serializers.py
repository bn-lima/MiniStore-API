from users import serializers
from rest_framework import serializers
from .models import MPPreference
from store.serializers import CouponResponseSerializer, CartResponseSerializer

class ContinueToPaymentResponseSerializer(serializers.Serializer):
    coupon = CouponResponseSerializer()
    cart = CartResponseSerializer()

class PreferenceResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = MPPreference
        fields = ('init_point', 'preference_id', 'expired')

class PayerSerializer(serializers.Serializer):
    client_full_name = serializers.CharField(max_length=200, required=True)
    client_cpf = serializers.CharField(max_length=11, required=True)
    client_email = serializers.EmailField(required=True)

    def validate_client_cpf(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("The cpf must only contain digits")
        return value
