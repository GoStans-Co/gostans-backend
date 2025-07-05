from django.urls import path
from customer_auth.views import (
    CustomerLoginView,
    CustomerUserSignupView,
    CustomTokenRefreshView,
    GoogleSignupAPIView,
    SendOTPView,
    VerifyOTPView,
)

urlpatterns = [
    path('login/', CustomerLoginView.as_view(), name='customer-login'),
    path('sign-up/', CustomerUserSignupView.as_view(), name='user-signup'),
    path('refresh-token/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('google/', GoogleSignupAPIView.as_view(), name='google-signup'),
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
]
