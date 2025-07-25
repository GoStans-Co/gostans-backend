from django.urls import path
from customer_auth.views import (
    CustomerLoginView,
    CustomerUserSignupView,
    CustomTokenRefreshView,
    GoogleSignupAPIView,
    SendOTPView,
    VerifyOTPView,
    ForgotPasswordView,
    ResendOTPView,
    VerifyOTPEmailView,
    ResetPasswordView,
    CheckEmailExistsView,
    ResendVerificationEmailView,
    VerifyEmailView,
    
)

urlpatterns = [
    path('login/', CustomerLoginView.as_view(), name='customer-login'),
    path('sign-up/', CustomerUserSignupView.as_view(), name='user-signup'),
    path('refresh-token/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('google/', GoogleSignupAPIView.as_view(), name='google-signup'),
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('verify-otp-email/', VerifyOTPEmailView.as_view(), name='resend-otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('check-email/', CheckEmailExistsView.as_view(), name='check_email'),
    path('resend-verification-email/', ResendVerificationEmailView.as_view(), name='check_email'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email')
]
