from django.apps import AppConfig
from django.contrib import admin

class AdminCustomConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "admin_custom"

    def ready(self):
        admin.site.site_header = "Gostance Admin Panel"
        admin.site.site_title = "Gostance Dashboard"
        admin.site.index_title = "Welcome to Gostance CMS"
