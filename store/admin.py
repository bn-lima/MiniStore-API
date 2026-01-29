from django.contrib import admin
from .models import Client, DiscountCoupon, Product, Cart, CartItem, Order, MPPreference, MpPayment, SupportChannel, SupportMessage

@admin.register(DiscountCoupon)
class DiscountCupomAdmin(admin.ModelAdmin):
    list_display = ('cupom','active','discount_percent','min_purchase')
    search_fields = ('cupom','active','discount_percent','min_purchase')
    exclude = ('used_by',)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('username','email','cpf','phone',)
    search_fields = ('username','cpf','phone','email')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name','category','price','stock', 'reserved_stock', 'active')
    search_fields = ('name','category','price','stock','reserved_stock','active')

class CartItemInline(admin.TabularInline): 
        model = CartItem
        extra = 1
        readonly_fields = ('subtotal',)

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin): 
    list_display = ('id', 'user', 'created_at', 'total','finalized','show_total_items', 'coupon')
    search_fields = ('user__username', 'user__email','finalized', 'coupon')
    inlines = [CartItemInline]
    readonly_fields = ('total',)

    def show_total_items(self, obj):
         return obj.total_items()
    show_total_items.short_description = 'total_items'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('user','status','order_id','created_at','updated_at','payment_method','discount_applied')
    search_fields = ('user','status','order_id','created_at','updated_at','payment_method','discount_applied')

@admin.register(MPPreference)
class MPPreferenceAdmin(admin.ModelAdmin):
    list_display = ('preference_id','value', 'expired', 'finalized', 'cart', 'init_point')
    search_fields = ('preference_id','value', 'expired', 'cart', 'finalized ')

@admin.register(MpPayment)
class MppaymentAdmin(admin.ModelAdmin):
    list_display = ('user','payment_id','preference','amount','created_at','payment_method', 'cart', 'finalized')
    search_fields = ('user','payment_id','preference','amount','created_at','payment_method', 'cart', 'finalized')

class SupportMessageInline(admin.TabularInline):
     model = SupportMessage
     extra = 1
     fields = ('message', 'date', 'user')
     readonly_fields = ('date', 'user')

@admin.register(SupportChannel)
class SupportChannelAdmin(admin.ModelAdmin):
     list_display = ('active', 'user', 'in_progress')
     search_fields = ('active', 'user', 'in_progress')
     inlines = [SupportMessageInline]