from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound
from .models import Country
from .serializers import CountryWithCitiesSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from common.utils import custom_response


class CountryWithCitiesAPIView(APIView):
    @swagger_auto_schema(
        operation_description="Retrieve a list of all countries along with their associated cities.",
        tags=["Public APIs"],
        responses={
            200: openapi.Response(
                description="Countries with cities retrieved successfully",
                examples={
                    "application/json": {
                        "status_code": 200,
                        "message": "Countries with cities retrieved successfully.",
                        "data": {
                            "country_data": [
                                {
                                    "id": 1,
                                    "name": "USA",
                                    "code": "US",
                                    "cities": [
                                        {"id": 101, "name": "New York"},
                                        {"id": 102, "name": "San Francisco"}
                                    ]
                                },
                                {
                                    "id": 2,
                                    "name": "India",
                                    "code": "IN",
                                    "cities": [
                                        {"id": 201, "name": "Mumbai"},
                                        {"id": 202, "name": "Delhi"}
                                    ]
                                }
                            ]
                        }
                    }
                }
            ),
            200: openapi.Response(
                description="No countries found",
                examples={
                    "application/json": {
                        "status_code": 200,
                        "message": "No countries found.",
                        "data": {
                            "country_data": []
                        }
                    }
                }
            )
        }
    )
    def get(self, request):
        countries = Country.objects.prefetch_related('cities').all()
        if not countries.exists():
            return custom_response(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="No countries found",
                data={}
            )

        serializer = CountryWithCitiesSerializer(countries, many=True)
        return custom_response(
            statusCode=status.HTTP_200_OK,
            message="Countries with cities retrieved successfully.",
            data={serializer.data}
        )
        
