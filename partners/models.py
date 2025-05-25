from django.db import models
from django.contrib.auth.models import User
from location.models import Country, City
from smart_selects.db_fields import ChainedForeignKey

class PartnerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='partner_profile')
    phone = models.CharField(max_length=20)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    #city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    city = ChainedForeignKey(
        City,
        chained_field="country",
        chained_model_field="country",
        show_all=False,
        auto_choose=True,
        sort=True,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    about = models.TextField(blank=True)
    tours_added = models.PositiveIntegerField(default=0)
    joined_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

    @property
    def first_name(self):
        return self.user.first_name

    @property
    def last_name(self):
        return self.user.last_name

    @property
    def email(self):
        return self.user.email