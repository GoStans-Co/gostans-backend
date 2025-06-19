from django.contrib.auth.models import User, Group
from rest_framework import serializers, status
from rest_framework.response import Response
from partners.models import PartnerProfile
from location.models import Country, City

class PartnerRegistrationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all())
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())
    about = serializers.CharField(allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=6)

    def validate_email(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password']
        )

        # Assign to 'Partner' group (create if it doesn't exist)
        group, created = Group.objects.get_or_create(name='Partner')
        user.groups.add(group)

        # Create PartnerProfile
        PartnerProfile.objects.create(
            user=user,
            phone=validated_data['phone'],
            country=validated_data['country'],
            city=validated_data['city'],
            about=validated_data['about']
        )

        return user
    
