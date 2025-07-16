from django.urls import path
from .views import TourListAPIView,TourDetailAPIView,TrendingToursAPIView,TopDestinationsAPIView


urlpatterns = [
    path('list/', TourListAPIView.as_view(), name='tour-list'),
    path('detail/<uuid:tour_uuid>/', TourDetailAPIView.as_view(), name='tour-detail'), 
    path('trending-tours/', TrendingToursAPIView.as_view(), name='trending-tours'),
    path('top-destinations/', TopDestinationsAPIView.as_view(), name='top-destinations'),
]
