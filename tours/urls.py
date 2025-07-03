from django.urls import path
from .views import TourListAPIView,TourDetailAPIView,WishlistAddAPIView, WishlistListAPIView,RemoveFromWishlistAPIView


urlpatterns = [
    path('tours/', TourListAPIView.as_view(), name='tour-list'),
    path('tours/<uuid:tour_uuid>/', TourDetailAPIView.as_view(), name='tour-detail'),
    path('wishlist/add/<uuid:tour_uuid>/', WishlistAddAPIView.as_view(), name='wishlist-add'),
    path('wishlist/', WishlistListAPIView.as_view(), name='wishlist-list'),
    path('wishlist/delete/<str:tour_uuid>/', RemoveFromWishlistAPIView.as_view(), name='wishlist-delete'),

]
