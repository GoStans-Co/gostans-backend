from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class CustomerAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'customer_auth'
    verbose_name = _("Customers")   # 👈 This changes sidebar app name
