from django.urls import path
from .views import AddToCartAPIView,CartListAPIView,RemoveFromCartAPIView

urlpatterns = [
    path('add/', AddToCartAPIView.as_view(), name='add-to-cart'),
    path('remove/<uuid:tour_uuid>/', RemoveFromCartAPIView.as_view(), name='remove-from-cart'),
    path('list/', CartListAPIView.as_view(), name='remove-from-cart'),

]