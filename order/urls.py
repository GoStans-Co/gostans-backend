from django.urls import path
from .views import AddToCartAPIView,CartListAPIView,RemoveFromCartAPIView,CreatePaymentView,ExecutePaymentView
from .views import PayPalWebhookView

urlpatterns = [
    path('add/', AddToCartAPIView.as_view(), name='add-to-cart'),
    path('remove/<uuid:tour_uuid>/', RemoveFromCartAPIView.as_view(), name='remove-from-cart'),
    path('list/', CartListAPIView.as_view(), name='remove-from-cart'),
    path('payments/create/', CreatePaymentView.as_view(), name='create-payment'),
    path('payments/execute/', ExecutePaymentView.as_view(), name='execute-payment'),
    path('paypal/webhook/', PayPalWebhookView.as_view(), name='paypal-webhook'),

]
