
from rest_framework import generics, status
from rest_framework.response import Response
from .serializers import PartnerRegistrationSerializer
from common.utils import custom_response  # assuming you use this
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class PartnerRegistrationAPIView(APIView):
    @swagger_auto_schema(
        operation_description="Register a new partner account.",
        request_body=PartnerRegistrationSerializer,
        responses={
            201: openapi.Response(
                description="Partner registered successfully",
                examples={
                    "application/json": {
                        "status": 201,
                        "message": "Partner registered successfully.",
                        "data": {
                            "username": "partner@example"
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Validation failed",
                examples={
                    "application/json": {
                        "status": 400,
                        "message": "Validation failed",
                        "data": {
                            "email": ["This field is required."],
                            "password": ["This field is required."]
                        }
                    }
                }
            )
        }
    )
    def post(self, request):
        serializer = PartnerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.is_staff = True 
            return custom_response(
                status_code=status.HTTP_201_CREATED,
                message="Partner registered successfully.",
                data={"username": user.username}
            )
        return custom_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Validation failed",
            data=serializer.errors
        )