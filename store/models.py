from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.db.models import Sum
import uuid
from store.constants import ProductCategory, OrderStatus
from users.models import Client
class DiscountCoupon(models.Model):

    cupom = models.CharField(max_length=10, blank=False)
    discount_percent = models.DecimalField(max_digits=5, default=0, decimal_places=2)

    min_purchase = models.DecimalField(max_digits=8,decimal_places=2, default=0)
    active = models.BooleanField(default=True)
    used_by = models.ManyToManyField(Client, blank=True, related_name='used_coupons')

    def is_active(self):
        return self.active
    
    def verify_min_purchase(self, price):
        if not self.min_purchase:
            return True
        return price >= self.min_purchase
    
    def apply_discount(self, price):
        if not self.is_active() or not self.verify_min_purchase(price):
            return price
        return price * (1 - self.discount_percent/100)

    def __str__(self):
        return f"{self.cupom} - {self.discount_percent}%"    
    


class Product(models.Model):


    name = models.CharField(max_length=200, blank=False)
    category = models.CharField(max_length=50,choices=ProductCategory.choices(), blank=False)
    price = models.DecimalField(decimal_places=2,max_digits=8, default=0)
    description = models.TextField()
    stock = models.IntegerField(default=0)
    reserved_stock = models.IntegerField(default=0)
    active = models.BooleanField(default=False)
    picture = models.ImageField(upload_to="products/", blank=False, null=False, default='default.jpg', )    

    slug = models.SlugField(max_length=255, unique=True, blank=True)

    def calculate_discount(self, cupom_code):
        try:
            discount = DiscountCoupon.objects.get(cupom = cupom_code)
        except DiscountCoupon.DoesNotExist:
            return self.price
        
        new_price = discount.apply_discount(self.price)
        return new_price            
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.price}"

class Cart(models.Model):

    user = models.ForeignKey(Client, on_delete=models.CASCADE)
    created_at = models.DateField(auto_now_add=True)
    finalized = models.BooleanField(default=False)

    passed_payment_step = models.BooleanField(default=False)
    passed_continue_to_payment = models.BooleanField(default=False)

    coupon = models.ForeignKey(DiscountCoupon, blank=True, null=True, on_delete=models.SET_NULL)

    preference = models.OneToOneField('Mppreference', blank=True, null=True, on_delete=models.SET_NULL)
    
    def total(self):
        return sum(item.subtotal() for item in self.items.all())
    
    def total_items(self):
        return self.items.aggregate(total=Sum('quantity')) ['total'] or 0 
    
    @classmethod
    def get_cart(cls, user):
        return cls.objects.get_or_create(user=user, finalized=False)
    
    def __str__(self):
        return f"{self.user} - {self.created_at}"



class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    
    is_reserved = models.BooleanField(default=False)

    class Meta:
        unique_together = ('cart', 'product')
       

    def subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.product} - {self.quantity}"
    

class Order(models.Model):

    user = models.ForeignKey(Client, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    status = models.CharField(max_length=18, choices=OrderStatus.choices(), default=OrderStatus.PENDING.value)
    order_id = models.UUIDField( default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField( default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    payment_method = models.CharField(max_length=50, blank=False, null=False)
    discount_applied = models.ForeignKey(DiscountCoupon, on_delete=models.SET_NULL, null=True, blank=True)

    total_price = models.DecimalField(
        decimal_places=2,
        max_digits=10,
        default=0
        )
    
class MPPreference(models.Model):

    preference_expiration = models.DateTimeField(editable=False)
    expired = models.BooleanField(default=False, editable=False)
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    preference_id = models.CharField(max_length=200, null=True, blank=True, editable=False)
    init_point = models.URLField(max_length=500, null=True, blank=True, editable=False)
    payer_email = models.EmailField(null=True, blank=True, editable=False)

    finalized = models.BooleanField(default=False)

    def is_preference_expired(self):
        if timezone.now() >=     self.preference_expiration:
            self.expired = True
            self.save()
            return True
        return False

class MpPayment(models.Model):
    user = models.ForeignKey(Client, on_delete=models.CASCADE, blank=False, related_name='payments')
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, blank=False, null=False)
    payment_id = models.CharField(max_length=200, null=True, blank=True, unique=True)
    preference = models.ForeignKey(MPPreference, on_delete=models.CASCADE, blank=False, null=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=200, null=True, blank=True)

    finalized = models.BooleanField(default=False)

class SupportMessage(models.Model):
    user = models.ForeignKey(Client, on_delete=models.CASCADE, blank=False, null=False)
    message = models.CharField(max_length=5000, blank=False)
    date = models.DateTimeField(auto_now=True)
    channel=models.ForeignKey('SupportChannel', on_delete=models.CASCADE, null=False, blank=False, related_name="messages")

    def __str__(self):
        return f"{self.user.username} - {self.date}"

class SupportChannel(models.Model):
    user = models.ForeignKey(Client, on_delete=models.CASCADE, null=False, blank=False)
    active = models.BooleanField(default=True)
    in_progress = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}"