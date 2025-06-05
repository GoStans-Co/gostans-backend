from rest_framework.views import APIView
from rest_framework.response import Response
from common.utils import custom_response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound
from .models import Country
from .serializers import CountryWithCitiesSerializer

class CountryWithCitiesAPIView(APIView):
    def get(self, request):
        countries = Country.objects.prefetch_related('cities').all()
        if not countries.exists():
            return custom_response(
                status_code=status.HTTP_200_OK,
                message="No countries found.",
                data={"country_data": []}
            )

        serializer = CountryWithCitiesSerializer(countries, many=True)
        return custom_response(
            status_code=status.HTTP_200_OK,
            message="Countries with cities retrieved successfully.",
            data={"country_data": serializer.data}
        )
        
