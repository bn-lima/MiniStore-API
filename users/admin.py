from django.contrib import admin
from users.models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('username','email','cpf','phone',)
    search_fields = ('username','cpf','phone','email')