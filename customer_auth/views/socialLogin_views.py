from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings
from common.social_auth import verify_telegram_auth,verify_facebook_token
from ..serializers import TelegramAuthSerializer,CustomerSocialSerializer,FacebookAuthSerializer
from common.utils import custom_response
from rest_framework import status
from ..models import CustomerUser
from rest_framework_simplejwt.tokens import RefreshToken


class TelegramSignupAPIView(APIView):

    @swagger_auto_schema(
        operation_description="Signup or login user with Telegram",
        request_body=TelegramAuthSerializer,
        tags=["Auth Controller"],
        responses={
            200: openapi.Response(
                description="Signup/Login successful",
                examples={"application/json": {"statusCode": 200, "message": "Signup successful", "data": {}}}
            ),
            400: openapi.Response(
                description="Invalid signature",
                examples={"application/json": {"statusCode": 400, "message": "Invalid signature", "data": {}}}
            ),
        }
    )
    
    def post(self, request):
        serializer = TelegramAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data.copy()
        
        bot_token = settings.TELEGRAM_BOT_TOKEN  
        if not verify_telegram_auth(data.copy(), bot_token):
            return custom_response(statusCode=status.HTTP_400_BAD_REQUEST, message="Invalid Telegram login signature",data=[])


        telegram_id = str(data['id'])
        user, created = CustomerUser.objects.get_or_create(
            oauth_id=telegram_id,
            defaults={
                "name": data.get("first_name", ""),
                "oauth_provider": "TELEGRAM",
                "email": None,  # Telegram doesn't provide email
                "phone": None,
                "image": data.get("photo_url", "")
            }
        )
        

        user_data = CustomerSocialSerializer(user).data
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)   # {'access': ..., 'refresh': ...}

        response_data = {
           **user_data,
            "oauthid": user.oauth_id,
            "oauthprovider": user.oauth_provider,
            "image": user.image,
            "refresh": str(refresh),
            "accesstoken": access_token,
        }

        return custom_response(
            statusCode= status.HTTP_200_OK,
            message= "Login successful" if not created else "Signup successful",
            data= response_data
        )


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
