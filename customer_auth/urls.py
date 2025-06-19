from django.urls import path
from .views import CustomerUserSignupView,CustomerUserUpdateView,CustomerUserProfileView,CustomerLoginView,CustomerUserImageUpdateView,CustomTokenRefreshView,GoogleSignupAPIView,SendOTPView,VerifyOTPView
from rest_framework.authtoken.views import obtain_auth_token


urlpatterns = [
    path('login/', CustomerLoginView.as_view(), name='customer-login'),
    path('sign-up/', CustomerUserSignupView.as_view(), name='user-signup'),
    path('update/', CustomerUserUpdateView.as_view(), name='user-update'),
    path('profile/', CustomerUserProfileView.as_view(), name='customer-profile'),
    path('updateimage/', CustomerUserImageUpdateView.as_view(), name='customer-image-update'),
    path('refresh-token/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('google/', GoogleSignupAPIView.as_view(), name='google-signup'),
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),


]
