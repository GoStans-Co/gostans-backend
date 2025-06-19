from rest_framework import serializers
from .models import CustomerUser
from django.contrib.auth.hashers import make_password,check_password
import re
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
import phonenumbers


class CustomerLoginSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email_or_phone = data.get('email_or_phone')
        password = data.get('password')
        

        user = None
        if '@' in email_or_phone:
            try:
                user = CustomerUser.objects.get(email=email_or_phone)
            except CustomerUser.DoesNotExist:
                raise AuthenticationFailed('No user with this email')
        else:
            try:
                user = CustomerUser.objects.get(phone=email_or_phone)
            except CustomerUser.DoesNotExist:
                raise AuthenticationFailed('No user with this phone number')

        if user and not check_password(password, user.password):
            raise AuthenticationFailed('Incorrect password')

        if not user.is_active:
            raise AuthenticationFailed('User is not active')

        data['user'] = user
        return data

class CustomerUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)  # Ensures password is not exposed in responses

    class Meta:
        model = CustomerUser
        fields = ['id', 'email', 'name', 'phone', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_phone(self, value):
        """Validate that the phone number is exactly 10 digits."""
        if not re.fullmatch(r"\d{10}", value):  
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")
        return value

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])  # Hash password
        return CustomerUser.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        """Handle user profile update"""
        instance.name = validated_data.get('name', instance.name)
        instance.phone = validated_data.get('phone', instance.phone)

        if 'password' in validated_data:
            instance.password = make_password(validated_data['password'])  # Hash new password

        instance.save()
        return instance

class CustomerUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerUser
        fields = ['id', 'email', 'name', 'phone','image']

    def to_representation(self, instance):
        print("Serializer - instance received:", instance)
        print("Serializer - instance.id:", instance.id)
        return super().to_representation(instance)


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = attrs['refresh']

        try:
            refresh_token = RefreshToken(refresh)
            data = {'access': str(refresh_token.access_token), 'refresh': str(refresh_token)}
            return data
        except TokenError as e:
            raise serializers.ValidationError({'refresh': 'Token is invalid or expired'})


class GoogleSerializer(serializers.Serializer):
    id_token = serializers.CharField()

class CustomerSocialSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerUser
        fields = ['id', 'email', 'name', 'phone']


class SendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)

    def validate_phone(self, value):
        try:
            parsed = phonenumbers.parse(value, None)
            if not phonenumbers.is_valid_number(parsed):
                raise serializers.ValidationError("Invalid phone number.")
        except Exception:
            raise serializers.ValidationError("Invalid phone number format.")
        return value
    
class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=4)