from django.contrib import admin
from .models import MpPayment, MPPreference

@admin.register(MPPreference)
class MPPreferenceAdmin(admin.ModelAdmin):
    list_display = ('preference_id','value', 'expired', 'finalized', 'init_point')
    search_fields = ('preference_id','value', 'expired', 'finalized ')

@admin.register(MpPayment)
class MppaymentAdmin(admin.ModelAdmin):
    list_display = ('user','payment_id','preference','amount','created_at','payment_method', 'cart', 'finalized')
    search_fields = ('user','payment_id','preference','amount','created_at','payment_method', 'cart', 'finalized')