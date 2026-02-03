from rest_framework import serializers
from rest_framework.authtoken.models import Token
from users.models import Client, PasswordResetToken
from users.auth_services import authenticate_client, validate_password

class ClientSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(max_length=150, write_only=True)
    
    class Meta:
        model = Client
        fields = ['id', 'username', 'password', 'confirm_password', 'cpf', 'location', 'phone', 'email']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, data):
        confirm_password = data.get('confirm_password')
        password = data.get('password')

        validated_password = validate_password(password, confirm_password)
        if not validated_password:
            raise serializers.ValidationError('Passwords do not match')
        return data

    def create(self, validated_data):

        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = Client.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        token, _= Token.objects.get_or_create(user=user)
        return user
    
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        token = authenticate_client(username, password)
        
        data['token'] = token
        
        return data
    
class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=150, write_only=True)
    new_password = serializers.CharField(max_length=150, write_only=True)

    def validate(self, data):
        user = self.context.get('user')
        current_password = data.get('password')
        new_password = data.get('new_password')

        if not user.check_password(current_password):
            raise serializers.ValidationError('Invalid password')
        
        if current_password == new_password:
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
        return token, user


class PasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField(max_length=150, required=True)
    confirm_new_password = serializers.CharField(max_length=150, required=True)
    
    def validate(self, data):
        new_password = data.get('new_password')
        confirm_new_password = data.get('confirm_new_password')

        password = validate_password(new_password, confirm_new_password)
        if not password:
            raise serializers.ValidationError('Passwords do not match')
        return data
    
    def save(self, **kwargs):
        new_password = self.validated_data.get('new_password')
        token = self.context.get('token')
        user = token.user

        if token.is_expired() or token.used == True:
            raise serializers.ValidationError('Token is expired or already used')
        
        user.set_password(new_password)
        token.mark_as_used()
        user.save()
        token.save()

    