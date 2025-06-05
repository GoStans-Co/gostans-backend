from django.urls import path
from .views import TourListAPIView,TourDetailAPIView,WishlistAddAPIView, WishlistListAPIView


urlpatterns = [
    path('tours/', TourListAPIView.as_view(), name='tour-list'),
    path('tours/<uuid:tour_uuid>/', TourDetailAPIView.as_view(), name='tour-detail'),
    path('wishlist/add/<uuid:tour_uuid>/', WishlistAddAPIView.as_view(), name='wishlist-add'),
    path('wishlist/', WishlistListAPIView.as_view(), name='wishlist-list'),
]
