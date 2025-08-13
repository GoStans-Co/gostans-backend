from django.urls import path
from .views import TourListAPIView,TourDetailAPIView,TrendingToursAPIView,TopDestinationsAPIView,ToursByDestinationAPIView,UpdateTourLocationView


urlpatterns = [
    path('list/', TourListAPIView.as_view(), name='tour-list'),
    path('detail/<uuid:tour_uuid>/', TourDetailAPIView.as_view(), name='tour-detail'), 
    path('trending-tours/', TrendingToursAPIView.as_view(), name='trending-tours'),
    path('top-destinations/', TopDestinationsAPIView.as_view(), name='top-destinations'),
    path('tours-by-destination/', ToursByDestinationAPIView.as_view(), name='tours-by-destination'),
    path('update-tour-location/', UpdateTourLocationView.as_view(), name='update-tour-location'),

    
]
