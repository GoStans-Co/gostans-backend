from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import PartnerProfile

@receiver(post_save, sender=User)
def create_partner_profile(sender, instance, created, **kwargs):
    if created and instance.is_staff:
        PartnerProfile.objects.create(user=instance)
