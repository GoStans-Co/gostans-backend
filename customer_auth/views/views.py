from rest_framework import status,generics,permissions,parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models import CustomerUser,CustomerOTP
from ..serializers import CustomerUserSerializer,CustomerLoginSerializer,CustomTokenRefreshSerializer,GoogleSerializer,CustomerSocialSerializer,SendOTPSerializer,VerifyOTPSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from customer_auth.authentication import CustomerUserJWTAuthentication
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import get_user_model
from rest_framework import status
from google.oauth2 import id_token
from google.auth.transport import requests
from google.auth.transport import requests as google_requests

import random
import string
from django.utils.crypto import get_random_string
from common.utils import custom_response
from common.social_auth import  generate_otp, send_otp_email, send_welcome_email
from datetime import timedelta
from django.utils import timezone
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.cache import cache
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from twilio.rest import Client
from django.conf import settings





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
            'user': user_data,
            "message": "Login successful. Please verify your email to unlock full features.",
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


class CheckEmailExistsView(APIView):

    @swagger_auto_schema(
        operation_description="Check if an email already exists in the system.",
        tags=["Auth Controller"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email"],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL)
            }
        ),
        responses={
            200: openapi.Response(
                description="Email existence result",
                examples={
                    "application/json": {
                        "email_exists": True
                    }
                }
            ),
            400: openapi.Response(
                description="Invalid request",
                examples={
                    "application/json": {
                        "error": "Email is required"
                    }
                }
            )
        }
    )
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        exists = CustomerUser.objects.filter(email=email).exists()
        return Response({'email_exists': exists}, status=status.HTTP_200_OK)

#User didn't receive the verification email during signup.
class ResendVerificationEmailView(APIView):

    @swagger_auto_schema(
        operation_description="Resend verification email to a user.",
        tags=["Auth Controller"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email"],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, format='email', description='Registered user email'),
            },
        ),
        responses={
            200: openapi.Response(
                description="Success response",
                examples={
                    "application/json": {"message": "Verification email resent"},
                },
            ),
            404: openapi.Response(
                description="User not found",
                examples={
                    "application/json": {"error": "User not found"},
                },
            ),
        },
    )
    def post(self, request):
        email = request.data.get('email')
        try:
            user = CustomerUser.objects.get(email=email)
            if user.is_email_verified:
                return Response({'message': 'Email already verified'}, status=200)

            user.email_verification_token = get_random_string(length=48)
            user.save()
            # Reuse send_verification_email logic
            CustomerUserSerializer().send_verification_email(user)
            return Response({'message': 'Verification email resent'}, status=200)
        except CustomerUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
 
# The user clicks the link in their email, and then this api would be called
class VerifyEmailView(APIView):
    @swagger_auto_schema(
        operation_description="Verify user email using token from email link.",
        tags=["Auth Controller"],
        manual_parameters=[
            openapi.Parameter(
                name="token",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="The email verification token sent to the user",
            )
        ],
        responses={
            200: openapi.Response(
                description="Email verified successfully",
                examples={
                    "application/json": {
                        "status": 200,
                        "message": "Email verified successfully!",
                        "data": {}
                    }
                }
            ),
            400: openapi.Response(
                description="Invalid or expired token",
                examples={
                    "application/json": {
                        "status": 400,
                        "message": "Invalid or expired token.",
                        "data": {}
                    }
                }
            )
        }
    )
    def get(self, request):
        token = request.GET.get('token')
        try:
            user = CustomerUser.objects.get(email_verification_token=token)
            user.is_email_verified = True
            user.email_verification_token = None  # Invalidate token
            user.save()

            # Now send welcome email
            send_welcome_email(user)

            return custom_response(200, "Email verified successfully!", {})
        except CustomerUser.DoesNotExist:
            return custom_response(400, "Invalid or expired token.", {})

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

            if created:
                send_welcome_email(user)

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
        

#send otp on phone
class SendOTPView(APIView):
    @swagger_auto_schema(
        operation_summary="send OTP on mobile number",
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
        
        try:
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )

            message = client.messages.create(
                body=f"Your OTP is {otp_code}. It will expire in 5 minutes.",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone
            )

        except Exception as e:
            return custom_response(
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to send OTP via SMS",
                data={"error": str(e)}
            )

        return custom_response(
            statusCode=status.HTTP_200_OK,
            data={"phone": phone},
            message="OTP sent successfully"
        )
    
#verify otp of phone number
class VerifyOTPView(APIView):
    
    @swagger_auto_schema(
        operation_summary="Verify OTP sent on mobile",
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
            return custom_response(statusCode=status.HTTP_400_BAD_REQUEST, message="Invalid data", data=serializer.errors)

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
            return custom_response(statusCode=status.HTTP_400_BAD_REQUEST, message="Invalid or expired OTP")

        # OTP verified successfully, delete it (one-time use)
        otp_obj.delete()

        # TODO: Perform user login/signup or token generation here

        return custom_response(statusCode=status.HTTP_200_OK, message="OTP verified successfully")


class ForgotPasswordView(APIView):
    @swagger_auto_schema(
        operation_summary="Request OTP for password reset",
        tags=["Auth Controller"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL),
            },
            example={"email": "user@example.com"}
        ),
        responses={
            200: openapi.Response(
                description="OTP sent",
                examples={
                    "application/json": {
                        "statusCode": 200,
                        "message": "OTP sent to your email",
                        "data": {}
                    }
                }
            ),
            404: openapi.Response(
                description="User not found",
                examples={
                    "application/json": {
                        "statusCode": 404,
                        "message": "User not found",
                        "data": {}
                    }
                }
            ),
            400: openapi.Response(
                description="Missing email",
                examples={
                    "application/json": {
                        "statusCode": 400,
                        "message": "Email is required",
                        "data": {}
                    }
                }
            ),
        }
    )
    def post(self, request):
        email = request.data.get('email')

        if not email:
            return custom_response(statusCode=status.HTTP_400_BAD_REQUEST, message="Email is required")
        
        try:
            user = CustomerUser.objects.get(email=email)
        except CustomerUser.DoesNotExist:
            return custom_response(statusCode=status.HTTP_400_BAD_REQUEST, message="User not found")

        otp = generate_otp()
        send_otp_email(email, otp,name=user.name or "User")

        # Save OTP in memory (using Redis cache)
        cache.set(f"otp:{email}", otp, timeout=300)

        return custom_response(statusCode=status.HTTP_200_OK, message="OTP sent to your email")

#resend otp on email
class ResendOTPView(APIView):
    @swagger_auto_schema(
        operation_summary="Resend OTP for password reset",
        tags=["Auth Controller"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL),
            },
            example={"email": "user@example.com"}
        ),
        responses={
            200: openapi.Response(
                description="OTP resent",
                examples={
                    "application/json": {
                        "statusCode": 200,
                        "message": "OTP resent to your email",
                        "data": {}
                    }
                }
            ),
            404: openapi.Response(
                description="User not found",
                examples={
                    "application/json": {
                        "statusCode": 404,
                        "message": "User not found",
                        "data": {}
                    }
                }
            ),
            429: openapi.Response(
                description="Too many requests",
                examples={
                    "application/json": {
                        "statusCode": 429,
                        "message": "OTP was already sent recently. Please wait.",
                        "data": {}
                    }
                }
            ),
        }
    )
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return custom_response(statusCode=status.HTTP_400_BAD_REQUEST, message="Email is required")

        try:
            user = CustomerUser.objects.get(email=email)
        except CustomerUser.DoesNotExist:
            return custom_response(statusCode=status.HTTP_400_BAD_REQUEST, message="User not found")

        # Cooldown key to prevent spam
        cooldown_key = f"otp:resend_lock:{email}"
        if cache.get(cooldown_key):
            return custom_response(statusCode=status.HTTP_429_TOO_MANY_REQUESTS, message="OTP was already sent recently. Please wait.")

        # Generate or reuse OTP
        otp = generate_otp()
        cache.set(f"otp:{email}", otp, timeout=300)  # Reset OTP with 5 min TTL
        cache.set(cooldown_key, True, timeout=30)    # Cooldown for 30 seconds

        send_otp_email(email, otp,name=user.name or "User")
        return custom_response(statusCode=status.HTTP_200_OK, message="OTP resent to your email")

# verify otp on email
class VerifyOTPEmailView(APIView):
    @swagger_auto_schema(
        operation_summary="Verify OTP for password reset",
        tags=["Auth Controller"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "otp"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL),
                "otp": openapi.Schema(type=openapi.TYPE_STRING, description="OTP sent to email"),
            },
            example={"email": "user@example.com", "otp": "1234"}
        ),
        responses={
            200: openapi.Response(
                description="OTP verified successfully",
                examples={
                    "application/json": {
                        "statusCode": 200,
                        "message": "OTP verified successfully",
                        "data": {}
                    }
                }
            ),
            400: openapi.Response(
                description="Invalid or expired OTP",
                examples={
                    "application/json": {
                        "statusCode": 400,
                        "message": "Invalid or expired OTP",
                        "data": {}
                    }
                }
            ),
            404: openapi.Response(
                description="User not found",
                examples={
                    "application/json": {
                        "statusCode": 404,
                        "message": "User not found",
                        "data": {}
                    }
                }
            ),
        }
    )
    def post(self, request):
        email = request.data.get("email")
        otp_submitted = request.data.get("otp")

        if not email or not otp_submitted:
            return custom_response(400, "Email and OTP are required")

        try:
            user = CustomerUser.objects.get(email=email)
        except CustomerUser.DoesNotExist:
            return custom_response(statusCode=status.HTTP_400_BAD_REQUEST, message="User not found")

        # Fetch OTP from cache
        otp_cached = cache.get(f"otp:{email}")

        if otp_cached is None:
            return custom_response(statusCode=status.HTTP_400_BAD_REQUEST, message="OTP expired or not found")

        if str(otp_cached) != str(otp_submitted):
            return custom_response(statusCode=status.HTTP_400_BAD_REQUEST, message="Invalid OTP")

        # Optionally: delete the OTP after successful verification
        cache.delete(f"otp:{email}")

        return custom_response(statusCode=status.HTTP_200_OK, message="OTP verified successfully")

#resest password
class ResetPasswordView(APIView):
    @swagger_auto_schema(
        operation_summary="Reset user password",
        tags=["Auth Controller"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "new_password"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL),
                "new_password": openapi.Schema(type=openapi.TYPE_STRING),
            },
            example={"email": "user@example.com", "new_password": "new_secure_password123"}
        ),
        responses={
            200: openapi.Response(
                description="Password reset successfully",
                examples={"application/json": {"statusCode": 200, "message": "Password reset successful", "data": {}}}
            ),
            404: openapi.Response(
                description="User not found",
                examples={"application/json": {"statusCode": 404, "message": "User not found", "data": {}}}
            ),
        }
    )
    def post(self, request):
        email = request.data.get('email')
        new_password = request.data.get('new_password')

        if not email or not new_password:
            return custom_response(statusCode=status.HTTP_400_BAD_REQUEST, message="Email and new password are required")

        try:
            user = CustomerUser.objects.get(email=email)
        except CustomerUser.DoesNotExist:
            return custom_response(statusCode=status.HTTP_400_BAD_REQUEST, message="User not found")

        user.password = make_password(new_password)
        user.save()

        # Optional: Invalidate existing OTP
        cache.delete(f"otp:{email}")

        return custom_response(statusCode=status.HTTP_200_OK, message="Password reset successful")

#new oath exchange api
class OAuthExchangeAPIView(APIView):

    @swagger_auto_schema(
        operation_description="Exchange authorization code for tokens and login/signup user with Google OAuth2.",
        tags=["Auth Controller"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["provider", "authorization_code", "redirect_uri"],
            properties={
                "provider": openapi.Schema(type=openapi.TYPE_STRING, example="google"),
                "authorization_code": openapi.Schema(type=openapi.TYPE_STRING, example="abcd......"),
                "redirect_uri": openapi.Schema(type=openapi.TYPE_STRING, example="http://localhost:5173/oauth2/redirect"),
            },
        ),
        responses={
            200: openapi.Response(
                description="Signup/Login successful",
                examples={
                    "application/json": {
                        "statusCode": 200,
                        "message": "Login successful",
                        "data": {
                            "id": 1,
                            "email": "user@example.com",
                            "name": "John Doe",
                            "phone": None,
                            "oauth_id": "google-oauth-id",
                            "oauth_provider": "GOOGLE",
                            "refresh": "refresh-token-string",
                            "access_token": "access-token-string",
                            "imageURL": "https://lh3.googleusercontent.com/a-/AOh14Gh...",
                            "oauthProvider": "GOOGLE",
                            "oauthId": "google-oauth-id",
                            "providerId": "google-oauth-id"
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Invalid request or failed exchange",
                examples={
                    "application/json": {
                        "statusCode": 400,
                        "message": "Failed to exchange code",
                        "data": {}
                    }
                }
            ),
        },
    )
    
    def post(self, request):
        provider = request.data.get("provider")
        code = request.data.get("authorization_code")
        redirect_uri = request.data.get("redirect_uri")

        if provider != "google":
            return custom_response(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="Only Google OAuth is supported",
                data={}
            )

        try:
            # 1. Exchange authorization code for access_token + id_token
            token_url = "https://oauth2.googleapis.com/token"
            payload = {
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
            token_resp = requests.post(token_url, data=payload)
            token_data = token_resp.json()

            if "id_token" not in token_data:
                return Response(
                    {"message": "Failed to exchange code", "data": token_data, "statusCode": 400},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            id_token_str = token_data["id_token"]

            # 2. Verify ID token
            idinfo = id_token.verify_oauth2_token(
                id_token_str, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )

            email = idinfo.get("email")
            first_name = idinfo.get("given_name", "")
            last_name = idinfo.get("family_name", "")
            name = f"{first_name} {last_name}".strip()
            image = idinfo.get("picture", "")
            oauth_id = idinfo.get("sub")

            # 3. Find or create user
            user, created = CustomerUser.objects.get_or_create(
                email=email,
                defaults={
                    "name": name or email.split("@")[0],
                    "oauth_id": oauth_id,
                    "oauth_provider": "GOOGLE",
                    "image": image,
                    "password": get_random_string(length=32),
                },
            )

            if created:
                send_welcome_email(user)

            # 4. Generate JWT
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            return Response(
                {
                    "message": "Signup successful" if created else "Login successful",
                    "data": {
                        "id": user.id,
                        "email": user.email,
                        "name": user.name,
                        "phone": user.phone,
                        "oauth_id": user.oauth_id,
                        "oauth_provider": user.oauth_provider,
                        "refresh": str(refresh),
                        "access_token": access_token,
                        "imageURL": image,
                        "oauthProvider": "GOOGLE",
                        "oauthId": oauth_id,
                        "providerId": oauth_id,
                    },
                    "statusCode": 200,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"message": "OAuth exchange failed", "error": str(e), "statusCode": 400},
                status=status.HTTP_400_BAD_REQUEST,
            )