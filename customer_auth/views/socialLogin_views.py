from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings
from common.social_auth import verify_telegram_auth,verify_facebook_token
from ..serializers import CustomerSocialSerializer,FacebookAuthSerializer
from common.utils import custom_response
from rest_framework import status
from ..models import CustomerUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache
import logging
import httpx
from django.db.models import Q


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FacebookSignupAPIView(APIView):
    @swagger_auto_schema(
        operation_description="Signup or login user with Facebook .",
        request_body=FacebookAuthSerializer,
        tags=["Auth Controller"],
        responses={
            200: openapi.Response(
                description="Signup/Login successful",
                examples={
                    "application/json": {
                        "statusCode": 200,
                        "message": "Signup successful",
                        "data": {
                            "uuid": "ysyiuaysuy",
                            "email": "user@example.com",
                            "name": "John Doe",
                            "oauth_id": "facebook-user-id",
                            "oauth_provider": "FACEBOOK",
                            "refresh": "refresh-token",
                            "access_token": "access-token"
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Invalid Facebook access token",
                examples={"application/json": {"statusCode": 400, "message": "Invalid Facebook token", "data": {}}}
            )
        }
    )
    def post(self, request):
        serializer = FacebookAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access_token = serializer.validated_data["access_token"]

        fb_data = verify_facebook_token(access_token)
        if not fb_data:
            return custom_response(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="Invalid Facebook access token",
                data={}
            )

        user, created = CustomerUser.objects.get_or_create(
            oauth_id=fb_data["id"],
            oauth_provider="FACEBOOK",
            defaults={
                "name": fb_data.get("name", ""),
                "email": fb_data.get("email"),  # may be None if user hasn't shared it
                "image": fb_data.get("picture", {}).get("data", {}).get("url"),
            }
        )

        refresh = RefreshToken.for_user(user)
        user_data = CustomerSocialSerializer(user).data

        return custom_response(
            statusCode=200,
            message="Signup successful" if created else "Login successful",
            data={
                **user_data,
                "oauth_id": user.oauth_id,
                "oauth_provider": user.oauth_provider,
                "refresh": str(refresh),
                "access_token": str(refresh.access_token),
                "oauthProvider": "FACEBOOK",
            }
        )


class VerifyTelegramOTPAPIView(APIView):
    def post(self, request):
        otp = request.data.get("otp")
        if not otp:
            return custom_response(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="OTP required",
                data={}
            )
        
        data = cache.get(f"telegram_login_{otp}")
       
        logger.info(f" Cache data: {data}")

        if not data:
            return custom_response(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="Invalid or expired OTP",
                data={}
            )

        user_id = data["user_id"]
        phone = data["phone"]
        name = data["name"]
        email =data["email"]
        
        existing_user = CustomerUser.objects.filter(Q(phone=phone) | Q(email=email)).first()
        if existing_user:
            if existing_user.oauth_provider != "TELEGRAM":
                existing_user.oauth_id = str(user_id)
                existing_user.oauth_provider = "TELEGRAM"
                existing_user.save()
            user = existing_user
            created = False
        else:
            user = CustomerUser.objects.create(
                oauth_id=str(user_id),
                phone=phone,
                oauth_provider="TELEGRAM",
                name=name,
                email=email
            )
            created = True

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        user_data = CustomerSocialSerializer(user).data
        

        def send_telegram_message(user_id: int, message: str):
            bot_token = settings.TELEGRAM_BOT_TOKEN
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": user_id,
                "text": message,
            }
            try:
                response = httpx.post(url, json=payload)
                response.raise_for_status()
            except Exception as e:
                logger.error(f"Error sending Telegram message: {e}")

        login_msg = "🎉 Signup successful!" if created else "✅ Login successful!"
        send_telegram_message(user_id, login_msg)

        return custom_response(
            statusCode=status.HTTP_200_OK,
            message="Login successful" if not created else "Signup successful",
            data={
                **user_data,
                "oauthId": user.oauth_id,
                "oauthProvider": user.oauth_provider,
                "refresh": str(refresh),
                "accessToken": access_token,
            }
        )

   
        otp = request.data.get("otp")
        if not otp:
            return custom_response(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="OTP required",
                data={}
            )
        user_id = cache.get(f"user_id_for_otp_{otp}")
        phone = cache.get(f"phone_for_otp_{otp}")
        name = cache.get(f"name_for_otp_{otp}")

        phone = None
        if not user_id or not phone or not name:
            return custom_response(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="Invalid or expired OTP",
                data={}
            )
        
        user, created = CustomerUser.objects.get_or_create(
            oauth_id=str(user_id),
            defaults={
                "phone": phone,
                "oauth_provider": "TELEGRAM",
                "name": name,
                "email": None,
                "image": ""
            }
        )

        user_data = CustomerSocialSerializer(user).data
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        response_data = {
            **user_data,
            "oauthid": user.oauth_id,
            "oauthprovider": user.oauth_provider,
            "image": user.image,
            "refresh": str(refresh),
            "accesstoken": access_token,
        }

        return custom_response(
            statusCode=status.HTTP_200_OK,
            message="Login successful" if not created else "Signup successful",
            data=response_data
        )