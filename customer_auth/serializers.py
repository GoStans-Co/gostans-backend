from rest_framework import serializers
from .models import CustomerUser
from django.contrib.auth.hashers import make_password,check_password
import re
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from tours.serializers import WishlistTourSerializer
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
import phonenumbers
from order.models import SavedCard
from common.social_auth import  generate_otp,send_verification_email, send_welcome_email
from django.utils.crypto import get_random_string





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

            pattern = r'^\+\d{10,15}$'
            if not re.fullmatch(pattern, value):
                raise serializers.ValidationError(
                    "Phone number must be in the format +[countrycode][number], "
                    "with 10 to 15 digits, e.g. +8201072646105."
                )
            return value

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])  # Hash password
        user = CustomerUser.objects.create(**validated_data)
        user.email_verification_token = get_random_string(length=48)
        user.save()

        send_verification_email(user)

        return user
    
    def update(self, instance, validated_data):
        """Handle user profile update"""
        instance.name = validated_data.get('name', instance.name)
        instance.phone = validated_data.get('phone', instance.phone)

        if 'password' in validated_data:
            instance.password = make_password(validated_data['password'])  # Hash new password

        instance.save()
        return instance

       
class CustomerUserProfileSerializer(serializers.ModelSerializer):
    wishlists = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)

    class Meta:
        model = CustomerUser
        fields = ['id', 'email', 'name', 'phone','image','date_joined', 'updated_at', 'is_verified', 'wishlists']

    def get_is_verified(self, obj):
        return obj.is_active

    def get_wishlists(self, obj):
        wishlist_qs = obj.wishlists.select_related('tour')
        return WishlistTourSerializer(wishlist_qs, many=True).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Rename date_joined to dateJoined
        data['dateJoined'] = data.pop('date_joined', None)
        data['isVerified'] = data.pop('is_verified', None)
        data['updatedAt'] = data.pop('updated_at', None)
        data['wishLists'] = data.pop('wishlists', None)

        return data


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


class TelegramAuthSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    photo_url = serializers.URLField(required=False)
    auth_date = serializers.IntegerField()
    hash = serializers.CharField()

class FacebookAuthSerializer(serializers.Serializer):
    access_token = serializers.CharField()