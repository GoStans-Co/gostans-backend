from django.urls import path
from customer_auth.views import (
    CustomerUserProfileView,
    CustomerUserUpdateView,
    CustomerUserImageUpdateView,WishlistAddAPIView,WishlistListAPIView,RemoveFromWishlistAPIView
    
)
from customer_auth.views.user_views import (
    AddToCartAPIView,RemoveFromCartAPIView,CartListAPIView
)

from order.views import(CreatePaymentView,ExecutePaymentView,PayPalWebhookView,CancelBookingView,CardBookingView,PaymentStatusView)
from tours.views import(SubmitRatingView)

urlpatterns = [
    path('profile/', CustomerUserProfileView.as_view(), name='customer-profile'),
    path('update/', CustomerUserUpdateView.as_view(), name='user-update'),
    path('update-image/', CustomerUserImageUpdateView.as_view(), name='customer-image-update'),
    path('wishlist/add/<uuid:tour_uuid>/', WishlistAddAPIView.as_view(), name='wishlist-add'),
    path('wishlist/', WishlistListAPIView.as_view(), name='wishlist-list'),
    path('wishlist/delete/<str:tour_uuid>/', RemoveFromWishlistAPIView.as_view(), name='wishlist-delete'),
    path('addTocart/', AddToCartAPIView.as_view(), name='add-to-cart'),
    path('removeCart/<uuid:tour_uuid>/', RemoveFromCartAPIView.as_view(), name='remove-from-cart'),
    path('cartList/', CartListAPIView.as_view(), name='remove-from-cart'),
    path('payments/create/', CreatePaymentView.as_view(), name='create-payment'),
    path('payments/execute/', ExecutePaymentView.as_view(), name='execute-payment'),
    path('paypal/webhook/', PayPalWebhookView.as_view(), name='paypal-webhook'),
    path('cancelTour/', CancelBookingView.as_view(), name='Cancel-tour'),
    path("ratetour/<uuid:tour_uuid>/rate/", SubmitRatingView.as_view(), name="submit-tour-rating"),
    path("payments/card/", CardBookingView.as_view(), name="card-booking"),
    path('payment-status/', PaymentStatusView.as_view(), name='payment-status'),

]
