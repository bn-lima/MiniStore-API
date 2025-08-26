from django.db import models
from django.core.validators import RegexValidator

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

    def calculate_discount(self, cupom_code):
        try:

            discount = DiscountCupom.objects.get(cupom = cupom_code)
            new_price = discount.apply_discount(self.price)
            return new_price            

        except DiscountCupom.DoesNotExist:
            return self.price
        
numeric_validator = RegexValidator(r'^\d{11}$', 'Enter exactly 11 numbers')

class Client(models.Model):
    name = models.CharField(max_length=150, blank=False)
    password = models.CharField(max_length=100)
    email = models.EmailField(blank=False)
    cpf = models.CharField(max_length=11, validators=[numeric_validator], blank=False)
    location = models.CharField(max_length=200, blank=False)
    phone = models.CharField(max_length=11, validators=[numeric_validator], blank=False)

#=========== Criar um modelo personalizado de carrinho ===========