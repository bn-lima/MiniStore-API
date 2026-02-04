from django.contrib import admin
from .models import SupportMessage, SupportChannel

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
