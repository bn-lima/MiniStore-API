from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
from django.utils import timezone
from django.db.models import Sum
import uuid

class DiscountCupom(models.Model):

    cupom = models.CharField(max_length=10, blank=False)
    discount_percent = models.DecimalField(max_digits=5, blank=False, null=False, decimal_places=2)

    min_purchase = models.DecimalField(max_digits=8,decimal_places=2, null=True, blank=True)
    active = models.BooleanField(default=True)
    

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

    CATEGORY_CHOICES = [
    ("Electronics", "Electronics"),
    ("Clothing", "Clothing"),
    ("Footwear", "Footwear"),
    ("Home & Kitchen", "Home & Kitchen"),
    ("Books", "Books"),
    ("Toys & Games", "Toys & Games"),
]

    name = models.CharField(max_length=200, blank=False)
    category = models.CharField(max_length=50,choices=CATEGORY_CHOICES, blank=False)
    price = models.DecimalField(null=False,blank=False,decimal_places=2,max_digits=8)
    description = models.CharField(max_length=1000, blank=False)
    stock = models.IntegerField(blank=False,null=False)
    active = models.BooleanField(default=False)
    
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    def calculate_discount(self, cupom_code):
        try:
            discount = DiscountCupom.objects.get(cupom = cupom_code)
            new_price = discount.apply_discount(self.price)
            return new_price            

        except DiscountCupom.DoesNotExist:
            return self.price
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.price}"
        


numeric_validator = RegexValidator(r'^\d{11}$', 'Enter exactly 11 numbers')



class Client(AbstractUser):
    cpf = models.CharField(max_length=11, validators=[numeric_validator], blank=False)
    location = models.CharField(max_length=200, blank=False)
    phone = models.CharField(max_length=11, validators=[numeric_validator], blank=False)


class Cart(models.Model):

    user = models.ForeignKey(Client, on_delete=models.CASCADE)
    created_at = models.DateField(auto_now_add=True)
    finalized = models.BooleanField(default=False)

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

    class Meta:
        unique_together = ('cart', 'product')

    def subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.product} - {self.quantity}"
    
class Order(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"), 
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("out_for_delivery", "Out for delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    ]


    PAYMENT_METHOD__CHOICES = [
        
        ("card","Card"),
        ("pix", "Pix"),
        ("payment_slip", "Payment Slip"),
    ]


    user = models.ForeignKey(Client, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    order_id = models.UUIDField(blank=False, default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(blank=False, default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    payment_method = models.CharField(blank=False, max_length=20, choices=PAYMENT_METHOD__CHOICES)
    discount_applied = models.ForeignKey(DiscountCupom, on_delete=models.SET_NULL, null=True, blank=True)

    total_price = models.DecimalField(
        decimal_places=2,
        null=True,
        max_digits=10,
        blank=True,
        )