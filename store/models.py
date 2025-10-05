from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
import uuid
from django.utils import timezone
from datetime import timedelta


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
    cpf = models.CharField(max_length=11, validators=[numeric_validator], blank=False, unique=True)
    location = models.CharField(max_length=200, blank=False)
    phone = models.CharField(max_length=11, validators=[numeric_validator], blank=False)
    email = models.EmailField(unique=True, blank=False)


class Cart(models.Model):

    user = models.ForeignKey(Client, on_delete=models.CASCADE)
    created_at = models.DateField(auto_now_add=True)

    def total(self):
        return sum(item.subtotal() for item in self.items.all())
    
    def __str__(self):
        return f"{self.user} - {self.created_at}"



class CartItem(models.Model):

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")

    def subtotal(self):
        return self.product.price * self.quantity
    
    def __str__(self):
        return f"{self.product} - {self.quantity}"
    
def token_expiration():
    return timezone.now() + timedelta(hours=1)


class PasswordResetToken(models.Model):
    user = models.ForeignKey(Client, blank=False, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=token_expiration)
    used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def mark_as_used(self):
        self.used = True
        return self.used