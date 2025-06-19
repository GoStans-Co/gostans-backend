from django.urls import path
from .views import PartnerRegistrationAPIView

urlpatterns = [
    path('register-partner/', PartnerRegistrationAPIView.as_view(), name='register-partner'),
]
