from rest_framework import status,generics,permissions,parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import CustomerUser
from .serializers import CustomerUserSerializer,CustomerUserProfileSerializer,CustomerLoginSerializer,CustomTokenRefreshSerializer,GoogleSerializer,CustomerSocialSerializer
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
from common.utils import custom_response

User = CustomerUser  # Use this instead of get_user_model()

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class CustomerLoginView(APIView):
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
    def post(self, request):
        serializer = CustomerUserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User registered successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Update API - Update user details
class CustomerUserUpdateView(generics.UpdateAPIView):
    serializer_class = CustomerUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Return the logged-in user"""
        return self.request.user 

#api for fetching user profile
class CustomerUserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]
    def get(self, request):
        user = request.user
        serializer = CustomerUserProfileSerializer(user)
        return Response(serializer.data)

#api for update image
class CustomerUserImageUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def patch(self, request):
        user = request.user
        print(request.user)
        image = request.FILES.get('image')

        if not image:
            return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)

        user.image = image
        user.save()

        return Response({'message': 'Image updated successfully'}, status=status.HTTP_200_OK)

#'user': user_data
class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = CustomTokenRefreshSerializer

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

        return Response({
            'token': access_token,
            'refresh': str(refresh_token),
            
        }, status=status.HTTP_200_OK)


class GoogleSignupAPIView(APIView):
    def post(self, request):
        serializer = GoogleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token_str = serializer.validated_data['id_token']
        print("Received id_token:", id_token_str)  # print received token

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