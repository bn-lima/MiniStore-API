from rest_framework import serializers
from .models import Product, Cart, CartItem, Order, DiscountCoupon, SupportChannel, SupportMessage
from .services import verify_order_status, calculate_total_quantity, is_channel_in_progress
from .coupon import validate_and_apply_discount, mark_coupon_as_used
from .cart import get_cart_item
from store.constants import OrderStatus
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class CouponCodeSerializer(serializers.Serializer):
    coupon_code = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
        allow_null=True
    )




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

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountCoupon
        fields = '__all__'
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
            return None

        cart_item.save()

        return cart_item
class CartItemResponseSerializer(serializers.ModelSerializer):
    subtotal = serializers.SerializerMethodField()
    product_id = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        exclude = ('cart', 'product')

    def get_subtotal(self, obj):
        return obj.subtotal()
    
    def get_product_id(self, obj):
        return obj.product.id
    
    def get_product_name(self, obj):
        return obj.product.name
class CartResponseSerializer(serializers.ModelSerializer):
    total = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    items = CartItemResponseSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ('total', 'total_items', 'items')

    def get_total(self, obj):
        return obj.total()
    
    def get_total_items(self, obj):
        return obj.total_items()
    
    def get_items(self, obj):
        return obj.items.all()
    
class CouponResponseSerializer(serializers.ModelSerializer):
    coupon_code = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    is_coupon_applicable = serializers.SerializerMethodField()
    discounted_total = serializers.SerializerMethodField()
    discount_percent = serializers.SerializerMethodField()

    class Meta:
        model = DiscountCoupon
        fields = ('discount_percent', 'coupon_code', 'message', 'is_coupon_applicable', 'discounted_total')

    def get_coupon_code(self, obj):
        return self.context.get('coupon_code')
    
    def get_message(self, obj):
        cart = self.context.get('cart')

        _, message, _ = validate_and_apply_discount(obj, cart)
        return message
    
    def get_is_coupon_applicable(self, obj):
        cart = self.context.get('cart')

        _, _, applicable = validate_and_apply_discount(obj, cart)
        return applicable
    
    def get_discounted_total(self, obj):
        cart = self.context.get('cart')
        price_with_discount, _, _ = validate_and_apply_discount(obj, cart)
        return price_with_discount
    
    def get_discount_percent(self, obj):
        return int(obj.discount_percent)
class OrderUserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        exclude  = ('user',)

class ShowSupportMessagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportMessage
        exclude = ('channel',)

class SupportChannelSerializer(serializers.ModelSerializer):
    messages = ShowSupportMessagesSerializer(many=True, read_only=True)
    class Meta:
        model = SupportChannel
        fields = ('messages',)

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
    
class OrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'