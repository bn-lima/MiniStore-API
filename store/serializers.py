from rest_framework import serializers
from .models import Product, Cart, Client, CartItem, Order, DiscountCupom
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
    
class CouponCodeSerializer(serializers.Serializer):
    coupon_code = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    def validate_coupon_code(self, value):
        if value:
            if not DiscountCupom.objects.filter(cupom=value, active=True).exists():
                raise serializers.ValidationError('Invalid or inactive coupon')
        return value

class CartSerializer(serializers.ModelSerializer):
    total = serializers.SerializerMethodField()
    items = CartItemSerializer(many=True, read_only=True)
    message = serializers.SerializerMethodField()
    coupon_code = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()

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
    
    def get_total_items(self, obj):
        return obj.total_items()
    
class ClientSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(max_length=200, write_only=True)
    
    class Meta:
        model = Client
        fields = ['id', 'username', 'password', 'confirm_password', 'cpf', 'location', 'phone', 'email']
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


class CartItemQuantitySerializer(serializers.Serializer):
    product_quantity = serializers.IntegerField(default=1)

    def validate_product_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError('Quantity must be at least 1')
        return value
    
class OrderSerializer(serializers.ModelSerializer):
    coupon_code = serializers.CharField(max_length=10, required=False)
    total = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ('user','cart','status','order_id','created_at','updated_at','discount_applied')

    def validate_payment_method(self, value):
        if not value:
            raise serializers.ValidationError('You must provide a payment method')
        if value not in ['pix','card','payment_slip']:
            raise serializers.ValidationError('Invalid payment method')
        return value
    
    def get_total(self, _):
        coupon_code = self.context.get('coupon_code')
        cart = self.context.get('cart')

        if not coupon_code or coupon_code in ['None', 'null']:
            return cart.total()

        new_total, _ = validate_coupon(coupon_code, cart)
        return new_total
    
    def get_message(self, _):
        coupon_code = self.context.get('coupon_code')
        cart = self.context.get('cart')

        if not coupon_code or coupon_code in ['None', 'null']:
            return None
        
        _, message = validate_coupon(coupon_code, cart)
        return message
    
    def create(self, validated_data):
        user = self.context['request'].user
        cart = self.context.get('cart')
        code = self.context.get('coupon_code')
        validated_data.pop('coupon_code', None)

        try:
            discount = DiscountCupom.objects.get(cupom=code)
        except DiscountCupom.DoesNotExist:
            discount = None
        
        order = Order.objects.create(
            user=user,
            cart=cart,
            discount_applied=discount,
            **validated_data
        )
        
        for item in cart.items.all():
            if item.quantity > item.product.stock:
                raise serializers.ValidationError(f"Not enough stock for {item.product.name}")
            
            product = item.product
            product.stock -= item.quantity
            if product.stock <= 0:
                product.stock =0
                product.active = False
            product.save()

        cart.finalized = True
        cart.save()

        return order

class UpdateStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    
    def save(self):
        order = self.context.get('order')
        order.status = self.validated_data.get('status')
        order.save()
        return order