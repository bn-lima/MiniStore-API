from rest_framework import serializers
from .models import Product, Cart, Client, PasswordResetToken
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = '__all__'
        read_only_fields = ('user', 'created_at')
        

class ClientSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(max_length=150, write_only=True)
    
    class Meta:
        model = Client
        fields = ['id', 'username', 'password', 'confirm_password', 'cpf', 'location', 'phone']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, data):
        confirm_password = data.get('confirm_password')
        password = data.get('password')
        if password != confirm_password:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def create(self, validated_data):

        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = Client.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        token, _= Token.objects.get_or_create(user=user)
        return user
    
class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=150, write_only=True)
    new_password = serializers.CharField(max_length=150, write_only=True)

    def validate(self, data):
        user = self.context.get('user')
        old_password = data.get('password')
        new_password = data.get('new_password')

        if not user.check_password(old_password):
            raise serializers.ValidationError('Invalid password')
        
        if old_password == new_password:
            raise serializers.ValidationError("The new password must be different from your current password")
        return data
    
    def save(self, **kwargs):   
        user = self.context.get('user')
        new_password = self.validated_data.get('new_password')

        user.set_password(new_password)
        user.save()
        return user
    
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate(self, data):
        email = data.get('email')
        try:
            user = Client.objects.get(email=email)
        except Client.DoesNotExist:
            raise serializers.ValidationError('Invalid email or user does not exist')
        
        data['user'] = user
        return data
    
    def save(self, **kwargs):
        user = self.validated_data.get('user')
        token = PasswordResetToken.objects.create(user=user)
        return token