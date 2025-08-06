from django.db import models
from django.core.exceptions import ValidationError
import re
import uuid
from uuid25 import Uuid25
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def user_directory_path(instance, filename):
    # uploaded files will be stored in MEDIA_ROOT/customer_<id>/<filename>
    return f'customer_{instance.id}/{filename}'

def generate_uuid25():
    standard_uuid = uuid.uuid4()
    return Uuid25.from_uuid(standard_uuid).value

class CustomerUser(models.Model):
    id = models.CharField(primary_key=True, default=generate_uuid25, editable=False, max_length=25)
    email = models.EmailField(unique=True,verbose_name=_("Email"))
    name = models.CharField(max_length=255,verbose_name=_("Name"))
    phone = models.CharField(max_length=15, blank=True, null=True, unique=True, verbose_name=_("Phone"))
    password = models.CharField(max_length=255,verbose_name=_("Password"))  # Store as a hashed password
    is_active = models.BooleanField(default=True) 
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to=user_directory_path,max_length=500, null=True, blank=True)  # add on field

    oauth_id = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("OAuth ID"))
    oauth_provider = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("OAuth Provider"))
    is_email_verified = models.BooleanField(default=False, verbose_name=_("Is Email Verified"))
    email_verification_token = models.CharField(max_length=64, blank=True, null=True)


    def __str__(self):
        return self.email

    @property
    def is_authenticated(self):
        """Required by DRF permission classes"""
        return True 



class CustomerOTP(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=15, db_index=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    def is_expired(self):
        # OTP expires in 5 minutes
        return timezone.now() > self.created_at + timezone.timedelta(minutes=5)

    def __str__(self):
        return f"OTP for {self.phone} - Verified: {self.is_verified}"