from django.urls import path
from .views import TourListAPIView,TourDetailAPIView


urlpatterns = [
    path('tours/', TourListAPIView.as_view(), name='tour-list'),
    path('tours/<uuid:tour_uuid>/', TourDetailAPIView.as_view(), name='tour-detail'),
   
]
