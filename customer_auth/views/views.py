from rest_framework import status,generics,permissions,parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models import CustomerUser,CustomerOTP
from ..serializers import CustomerUserSerializer,CustomerUserProfileSerializer,CustomerLoginSerializer,CustomTokenRefreshSerializer,GoogleSerializer,CustomerSocialSerializer,SendOTPSerializer,VerifyOTPSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from customer_auth.authentication import CustomerUserJWTAuthentication
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import get_user_model
from rest_framework import status
from google.oauth2 import id_token
from google.auth.transport import requests
import random
import string
from django.utils.crypto import get_random_string
from common.utils import custom_response,generate_otp
from datetime import timedelta
from django.utils import timezone
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


User = CustomerUser  # Use this instead of get_user_model()

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class CustomerLoginView(APIView):

    @swagger_auto_schema(
        operation_description="User login to obtain JWT tokens.",
        tags=["Auth Controller"],
        request_body=CustomerLoginSerializer,
        responses={
            200: openapi.Response(
                description="Login successful",
                examples={
                    "application/json": {
                        "token": "access-token-string",
                        "refresh": "refresh-token-string",
                        "ip_address": "203.0.113.1",
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "name": "John Doe",
                            "phone": "1234567890"
                            # Add other user fields if any
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Validation error or invalid credentials",
                examples={
                    "application/json": {
                        "detail": "Invalid credentials"
                    }
                }
            )
        }
    )

    def post(self, request):
        serializer = CustomerLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        ip_address = get_client_ip(request)

        # Generate JWT Token
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        user_data = CustomerUserSerializer(user).data
        return Response({
            'token': access_token,
            'refresh': str(refresh),
            'ip_address': ip_address,
            'user': user_data
        }, status=status.HTTP_200_OK)
        

class CustomerUserSignupView(APIView):

    @swagger_auto_schema(
        operation_description="Register a new user.",
        tags=["Auth Controller"],
        request_body=CustomerUserSerializer,
        responses={
            201: openapi.Response(
                description="User registered successfully",
                examples={
                    "application/json": {
                        "status": 201,
                        "message": "User registered successfully!",
                        "data": {}
                    }
                }
            ),
            400: openapi.Response(
                description="Validation error",
                examples={
                    "application/json": {
                        "status": 400,
                        "message": "Validation error",
                        "data": {
                            "email": ["This field is required."],
                            "password": ["This field may not be blank."]
                        }
                    }
                }
            ),
        }
    )
    
    def post(self, request):
        serializer = CustomerUserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return custom_response(
                statusCode=status.HTTP_201_CREATED,
                message="User registered successfully!",
                data={}
            )
        return custom_response(
            statusCode=status.HTTP_400_BAD_REQUEST,
            message="Validation error",
            data=serializer.errors
        )


class CustomTokenRefreshView(TokenRefreshView):

    permission_classes = [AllowAny]
    serializer_class = CustomTokenRefreshSerializer

    @swagger_auto_schema(
        operation_description="Refresh JWT access token using a refresh token.",
        tags=["Auth Controller"],
        request_body=CustomTokenRefreshSerializer,
        responses={
            200: openapi.Response(
                description="Tokens refreshed successfully",
                examples={
                    "application/json": {
                        "status": 200,
                        "message": "Token refreshed successfully",
                        "data": {
                            "token": "new-access-token",
                            "refresh": "refresh-token"
                        }
                    }
                }
            ),
            401: openapi.Response(
                description="Invalid or expired refresh token",
                examples={
                    "application/json": {
                        "status": 401,
                        "message": "Invalid refresh token",
                        "data": {}
                    }
                }
            ),
            404: openapi.Response(
                description="User not found",
                examples={
                    "application/json": {
                        "status": 404,
                        "message": "User not found",
                        "data": {}
                    }
                }
            )
        }
    )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        refresh_token = request.data.get("refresh")
        access_token = serializer.validated_data['access']

        try:
            token_obj = RefreshToken(refresh_token)
            user_id = token_obj.payload.get('user_id')
            user = CustomerUser.objects.get(pk=user_id)  # Explicitly use CustomerUser
            user_data = CustomerUserSerializer(user).data
        except get_user_model().DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return custom_response(
            statusCode=status.HTTP_200_OK,
            message="Token refreshed successfully",
            data={
                "token": access_token,
                "refresh": str(refresh_token),
                # Optionally return user data
                # "user": CustomerUserSerializer(user).data
            }
        )


class GoogleSignupAPIView(APIView):
     
    @swagger_auto_schema(
        operation_description="Signup or login user with Google OAuth2 ID token.",
        tags=["Auth Controller"],
        request_body=GoogleSerializer,
        responses={
            200: openapi.Response(
                description="Signup/Login successful",
                examples={
                    "application/json": {
                        "statusCode": 200,
                        "message": "Signup successful",
                        "data": {
                            "id": 1,
                            "email": "user@example.com",
                            "name": "John Doe",
                            "phone": None,
                            "oauth_id": "google-oauth-id",
                            "oauth_provider": "GOOGLE",
                            "refresh": "refresh-token-string",
                            "access_token": "access-token-string",
                            "imageURL": "https://picture.url",
                            "oauthProvider": "GOOGLE",
                            "oauthId": "google-oauth-id",
                            "providerId": "google-oauth-id"
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Invalid Google ID token",
                examples={
                    "application/json": {
                        "statusCode": 400,
                        "message": "Invalid Google ID token",
                        "data": {}
                    }
                }
            )
        }
    )
     
    def post(self, request):
        serializer = GoogleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token_str = serializer.validated_data['id_token']
        #print("Received id_token:", id_token_str)  # print received token

        try:
            # Verify token
            idinfo = id_token.verify_oauth2_token(id_token_str, requests.Request())
            # Extract user info
            email = idinfo.get('email')
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            name = f"{first_name} {last_name}".strip()
            image = idinfo.get('picture', '')
            oauth_id = idinfo.get('sub')

            # Find or create user
            user, created = CustomerUser.objects.get_or_create(
                email=email,
                defaults={
                    'name': name or email.split('@')[0],
                    'phone': None,
                    'oauth_id': oauth_id,
                    'oauth_provider': 'GOOGLE',
                    'image': '',
                    'password': get_random_string(length=32),  # Will be hashed in model manager
                }
            )
            user_data = CustomerSocialSerializer(user).data
            # Generate JWT Token
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)   

            return Response({
                "message": "Signup successful" if created else "Login successful",
                "data": {
                    **user_data,
                    "refresh": str(refresh),
                    "access_token": access_token,
                    "imageURL": image,
                    "oauthProvider": "GOOGLE",
                    "oauthId": oauth_id,
                    "providerId": oauth_id
                },
                "statusCode": 200
            }, status=status.HTTP_200_OK)
        except ValueError:
            print("Token verification failed:")
            # Invalid token
            return Response({
                "message": "Invalid Google ID token",
                "data": {},
                "statusCode": 400
            }, status=status.HTTP_400_BAD_REQUEST)
        

class SendOTPView(APIView):
    @swagger_auto_schema(
        operation_description="Send OTP to the provided phone number. No authentication required.",
        tags=["Auth Controller"],
        request_body=SendOTPSerializer,
        responses={
            200: openapi.Response(
                description="OTP sent successfully",
                examples={
                    "application/json": {
                        "status": 200,
                        "message": "OTP sent successfully",
                        "data": {
                            "otp": "123456"
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Invalid phone number ",
                examples={
                    "application/json": {
                        "status": 400,
                        "message": "Invalid phone number ex:+8289562314",
                        "data": {
                            "phone": ["This field is required."]
                        }
                    }
                }
            )
        }
    )

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            # Use your custom response for validation errors
            return custom_response(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="Invalid phone number",
                data=serializer.errors
            )

        phone = serializer.validated_data['phone']
        otp_code = generate_otp()
        expires_at = timezone.now() + timedelta(minutes=5)

        # Save or update OTP
        CustomerOTP.objects.update_or_create(
            phone=phone,
            defaults={
                'otp': otp_code,
                'expires_at': expires_at
            }
        )

        # Here, just print OTP for demo
        print(f"Sending OTP {otp_code} to {phone}")

        return custom_response(
            statusCode=status.HTTP_200_OK,
            data={"otp": otp_code},
            message="OTP sent successfully"
        )
    

class VerifyOTPView(APIView):
    
    @swagger_auto_schema(
        operation_description="Verify otp.",
        tags=["Auth Controller"],
        request_body=VerifyOTPSerializer,
        responses={
            200: openapi.Response(
                description="OTP verified successfully",
                examples={
                    "application/json": {
                        "status": 200,
                        "message":"OTP verified successfully",
                    }
                }
            ),
            400: openapi.Response(
                description="Invalid or expired OTP",
                examples={
                    "application/json": {
                        "status": 400,
                        "message": "Invalid or expired OTP"
                    }
                }
            )
        }
    )

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return custom_response(statusCode=400, message="Invalid data", data=serializer.errors)

        phone = serializer.validated_data['phone']
        otp_input = serializer.validated_data['otp']

        # Delete expired OTPs for this phone
        CustomerOTP.objects.filter(phone=phone, expires_at__lt=timezone.now()).delete()

        # Check if OTP exists and is valid
        otp_obj = CustomerOTP.objects.filter(
            phone=phone,
            otp=otp_input,
            expires_at__gte=timezone.now()
        ).first()

        if not otp_obj:
            return custom_response(statusCode=400, message="Invalid or expired OTP")

        # OTP verified successfully, delete it (one-time use)
        otp_obj.delete()

        # TODO: Perform user login/signup or token generation here

        return custom_response(statusCode=200, message="OTP verified successfully")


