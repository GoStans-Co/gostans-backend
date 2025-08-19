# Import views from views.py
from .views import (
    CustomerLoginView,
    CustomerUserSignupView,
    CustomTokenRefreshView,
    GoogleSignupAPIView,
    SendOTPView,
    VerifyOTPView,ForgotPasswordView,ResendOTPView,VerifyOTPEmailView,ResetPasswordView,
    CheckEmailExistsView,ResendVerificationEmailView,VerifyEmailView,OAuthExchangeAPIView

)

# Import views from user_views.py
from .user_views import (
    CustomerUserProfileView,
    CustomerUserUpdateView,
    CustomerUserImageUpdateView,
    WishlistAddAPIView,
    WishlistListAPIView,
    RemoveFromWishlistAPIView,
    CartListAPIView,
    AddToCartAPIView,
    RemoveFromCartAPIView
)

# from order.views import(
#     AddToCartAPIView,
#     RemoveFromCartAPIView,
#     CartListAPIView
# )