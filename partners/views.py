
from rest_framework import generics, status
from rest_framework.response import Response
from .serializers import PartnerRegistrationSerializer
from common.utils import custom_response  # assuming you use this
from rest_framework.views import APIView


class PartnerRegistrationAPIView(APIView):
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