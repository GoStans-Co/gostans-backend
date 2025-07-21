from django.urls import path
from customer_auth.views.socialLogin_views import FacebookSignupAPIView,VerifyTelegramOTPAPIView

urlpatterns = [
    path("facebook/", FacebookSignupAPIView.as_view(), name="facebook-signup"),
    path("telegram/verify-otp/", VerifyTelegramOTPAPIView.as_view(), name="facebook-signup"),
    
]
