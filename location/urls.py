# locations/urls.py

from django.urls import path
from .views import CountryWithCitiesAPIView

urlpatterns = [
    path('countries-with-cities/', CountryWithCitiesAPIView.as_view(), name='countries-with-cities'),
]
