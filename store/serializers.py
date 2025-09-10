from rest_framework import serializers
from .models import Product, Cart, Client, CartItem, DiscountCupom
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from. services import validate_coupon


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class CartItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = '__all__'
        
    def get_subtotal(self, obj):
        return obj.subtotal()
    
class CartSerializer(serializers.ModelSerializer):
    total = serializers.SerializerMethodField()
    items = CartItemSerializer(many=True, read_only=True)
    message = serializers.SerializerMethodField()
    coupon_code = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = '__all__'
        read_only_fields = ('user', 'created_at')

    def get_total(self, obj):
        coupon_code = self.context.get('coupon_code')
        
        if not coupon_code or coupon_code in ["None", "null"]:
            return obj.total()
        
        new_total, _ = validate_coupon(coupon_code, obj)
        return new_total
        
    def get_message(self, obj):
        coupon_code = self.context.get('coupon_code')

        if not coupon_code or coupon_code in ["None", "null"]:
            return None
        
        _, message = validate_coupon(coupon_code, obj)
        return message
    
    def get_coupon_code(self, obj):
        return self.context.get('coupon_code')
    
class ClientSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(max_length=200, write_only=True)
    
    class Meta:
        model = Client
        fields = ['id', 'username', 'password', 'confirm_password', 'cpf', 'location', 'phone']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, data):
        confirm_password = data.get('confirm_password')
        password = data.get('password')
        if password != confirm_password:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def create(self, validated_data):

        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = Client.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        token, _= Token.objects.get_or_create(user=user)
        return user


class AddToCartSerializer(serializers.Serializer):

    product_quantity = serializers.IntegerField(default=1)

    def validate_product_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError('Quantity must be at least 1')
        return value
    
class DeleteCartItemSerializer(serializers.Serializer):

    product_quantity = serializers.IntegerField(default=1)

    def validate_product_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError('Quantity must be at least 0')
        return value