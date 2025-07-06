from django.urls import path
from .views import TourListAPIView,TourDetailAPIView


urlpatterns = [
    path('list/', TourListAPIView.as_view(), name='tour-list'),
    path('detail/<uuid:tour_uuid>/', TourDetailAPIView.as_view(), name='tour-detail'), 
]
