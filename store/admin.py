from django.contrib import admin
from .models import Client, DiscountCupom, Product, Cart, CartItem, Order

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
    list_display = ('id', 'user', 'created_at', 'total','finalized')
    search_fields = ('user__username', 'user__email','finalized')
    inlines = [CartItemInline]
    readonly_fields = ('total',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('user','status','order_id','created_at','updated_at','payment_method','discount_applied')
    search_fields = ('user','status','order_id','created_at','updated_at','payment_method','discount_applied')