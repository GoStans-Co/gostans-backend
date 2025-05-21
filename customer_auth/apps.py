from django.apps import AppConfig


class CustomerAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'customer_auth'

    def ready(self):
        import customer_auth.translation
