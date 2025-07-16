from django.urls import path
from customer_auth.views.socialLogin_views import TelegramSignupAPIView,FacebookSignupAPIView

urlpatterns = [
    path("telegram/", TelegramSignupAPIView.as_view(), name="telegram-signup"),
    path("facebook/", FacebookSignupAPIView.as_view(), name="facebook-signup"),

    
]
