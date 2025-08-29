from django.contrib import admin
from .models import Client, DiscountCupom, Product, Cart, CartItem

@admin.register(DiscountCupom)
class DiscountCupomAdmin(admin.ModelAdmin):
    list_display = ('cupom','active','discount_percent','min_purchase')
    search_fields = ('cupom','active','discount_percent','min_purchase')

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('username','email','cpf','phone')
    search_fields = ('username','cpf','phone','email')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name','category','price','stock')
    search_fields = ('name','category','price','stock')

class CartItemInline(admin.TabularInline):
        model = CartItem
        extra = 1
        readonly_fields = ('subtotal',)

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'total')
    search_fields = ('user__username', 'user__email')
    inlines = [CartItemInline]
    readonly_fields = ('total',)