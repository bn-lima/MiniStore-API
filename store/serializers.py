from rest_framework import serializers
from .models import Product, Cart, Client, CartItem, Order, DiscountCoupon, PasswordResetToken
from rest_framework.authtoken.models import Token
from .services import verify_order_status, calculate_total_quantity
from .auth import validate_password
from .coupon import validate_and_apply_discount, get_discount, calculate_total_price, mark_coupon_as_used
from .payment import finalize_preference
from .cart import get_cart_item

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
        
        discount = get_discount(coupon_code)
        
        new_total, _, _ = validate_and_apply_discount(discount, obj)
        return new_total
        
    def get_coupon_message(self, obj):
        coupon_code = self.context.get('coupon_code')

        if not coupon_code:
            return None

        discount = get_discount(coupon_code)

        _, message, _ = validate_and_apply_discount(discount, obj)
        return message
    
    def get_coupon_code(self, obj):
        coupon_code = self.context.get('coupon_code')

        if not coupon_code:
            return None
        return coupon_code
    
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

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ('user','cart','status','order_id','created_at','updated_at','discount_applied','total_price', 'payment_method')
    
    def create(self, validated_data):
        user = self.context.get('user')
        cart = self.context.get('cart')
        validated_data.pop('coupon_code', None)
        payment = self.context.get('payment')
        
        discount = cart.coupon

        if discount:
            used_coupon = mark_coupon_as_used(discount, user)

            if not used_coupon:
                raise serializers.ValidationError('Invalid coupon or already used.')

        order = Order.objects.create(
            user=user,
            cart=cart,
            discount_applied=discount if discount else None,
            total_price=payment.amount,
            payment_method=payment.payment_method,
            **validated_data
        )
        
        for item in cart.items.all():
            if item.quantity > item.product.stock:
                raise serializers.ValidationError(f"Not enough stock for {item.product.name}")
            
            product = item.product #MOVER ISSO PRA OUTRO ARQUIVO
            product.stock -= item.quantity#SUBTRAIR DO ESTOQUE QUANDO O PEDIDO FOR PAGO
            if product.stock <= 0:
                product.stock =0
                product.active = False
            product.save()

        cart.finalized = True
        cart.save()

        payment.finalized = True
        payment.save()
        
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
        model = DiscountCoupon
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


class AddToCartSerializer(serializers.Serializer):

    def validate(self, data):
        quantity = self.context.get('quantity')
        cart = self.context.get('cart')
        product = self.context.get('product')

        total_quantity = calculate_total_quantity(quantity, cart, product)

        if product.stock < total_quantity:
            raise serializers.ValidationError('The quantity to add exceeds available stock')
        
        data['total_quantity'] = total_quantity
        return data
        
    def save(self, **kwags):
        cart = self.context.get('cart')
        product = self.context.get('product')
        total_quantity = self.validated_data.get('total_quantity')

        cart_item = get_cart_item(cart, product)

        if not cart_item:
            cart_item = CartItem.objects.create(cart=cart, product=product, quantity=total_quantity)
        else:
            cart_item.quantity = total_quantity
            cart_item.save()

        return cart_item

class DeleteCartItemSerializer(serializers.Serializer):

    def validate(self, data):
        cart_item = self.context.get('cart_item')

        if not cart_item:
            raise serializers.ValidationError("This product doesn't exist in your cart")
        
        data['cart_item'] = cart_item
        return data
    
    def save(self, **kwargs):
        cart_item = self.validated_data.get('cart_item')
        quantity = self.context.get('quantity')

        cart_item.quantity -= quantity
        if cart_item.quantity <= 0:
            cart_item.delete()
            return None, None

        cart_item.save()
        subtotal = cart_item.subtotal()
        return cart_item, subtotal

