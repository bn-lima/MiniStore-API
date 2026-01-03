from rest_framework import serializers
from .models import Product, Cart, Client, CartItem, Order, DiscountCupom, PasswordResetToken
from rest_framework.authtoken.models import Token
from .services import verify_order_status
from .auth import validate_password
from .coupon import validate_coupon, get_discount, calculate_total_price
from .payment import finalize_preference

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
    coupon_message = serializers.SerializerMethodField()
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
        
    def get_coupon_message(self, obj):
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
    confirm_password = serializers.CharField(max_length=150, write_only=True)
    
    class Meta:
        model = Client
        fields = ['id', 'username', 'password', 'confirm_password', 'cpf', 'location', 'phone', 'email']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, data):
        confirm_password = data.get('confirm_password')
        password = data.get('password')

        validated_password = validate_password(password, confirm_password)
        if not validated_password:
            raise serializers.ValidationError('Passwords do not match')
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
    message = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ('user','cart','status','order_id','created_at','updated_at','discount_applied','total_price', 'payment_method')

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
        
        discount_obj = get_discount(code)

        _, discount = calculate_total_price(code, cart, discount_obj)
        
        preference = self.context.get('preference')

        order = Order.objects.create(
            user=user,
            cart=cart,
            discount_applied=discount if discount else None,
            total_price=preference.value,
            payment_method=preference.payment_method,
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

        finalize_preference(preference)
        verify_order_status(order.status, user.email, order)

        return order
    
class UserOrdersListSerializer(serializers.ModelSerializer):
    cart_id = serializers.SerializerMethodField()
    coupon_code = serializers.SerializerMethodField()
    discount_value = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["order_id", "status", "total_price", "created_at", "updated_at", "cart_id", "coupon_code", "discount_value"]

    def get_cart_id(self, obj):
        return obj.cart.pk
    
    def get_coupon_code(self, obj):
        if obj.discount_applied:
            return obj.discount_applied.cupom
        return None
    
    def get_discount_value(self, obj):
        if obj.discount_applied:
            return f"{obj.discount_applied.discount_percent} %"
        return None

class UpdateStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    
    def save(self, **kwargs):
        order = self.context.get('order')
        order.status = self.validated_data.get('status')
        order.save()

        verify_order_status(order.status, order.user.email, order)
        
        return order
    
class PayerSerializer(serializers.Serializer):
    client_full_name = serializers.CharField(max_length=200, required=True)
    client_cpf = serializers.CharField(max_length=11, required=True)
    client_email = serializers.EmailField(required=True)

    def validate_client_cpf(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("The cpf must only contain digits")
        return value

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountCupom
        fields = '__all__'

class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=150, write_only=True)
    new_password = serializers.CharField(max_length=150, write_only=True)

    def validate(self, data):
        user = self.context.get('user')
        old_password = data.get('password')
        new_password = data.get('new_password')

        if not user.check_password(old_password):
            raise serializers.ValidationError('Invalid password')
        
        if old_password == new_password:
            raise serializers.ValidationError("The new password must be different from your current password")
        return data
    
    def save(self, **kwargs):   
        user = self.context.get('user')
        new_password = self.validated_data.get('new_password')

        user.set_password(new_password)
        user.save()
        return user
    
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate(self, data):
        email = data.get('email')
        try:
            user = Client.objects.get(email=email)
        except Client.DoesNotExist:
            raise serializers.ValidationError('Invalid email or user does not exist')
        
        data['user'] = user
        return data
    
    def save(self, **kwargs):
        user = self.validated_data.get('user')
        token = PasswordResetToken.objects.create(user=user)
        return token, user


class PasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField(max_length=150, required=True)
    confirm_new_password = serializers.CharField(max_length=150, required=True)
    
    def validate(self, data):
        new_password = data.get('new_password')
        confirm_new_password = data.get('confirm_new_password')

        password = validate_password(new_password, confirm_new_password)
        if not password:
            raise serializers.ValidationError('Passwords do not match')
        return data
    
    def save(self, **kwargs):
        new_password = self.validated_data.get('new_password')
        token = self.context.get('token')
        user = token.user

        if token.is_expired() or token.used == True:
            raise serializers.ValidationError('Token is expired or already used')
        
        user.set_password(new_password)
        token.mark_as_used()
        user.save()
        token.save()
