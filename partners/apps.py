from django.apps import AppConfig

def ready(self):
    import partners.signals

class PartnersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'partners'



