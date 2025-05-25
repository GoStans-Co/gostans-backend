from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Country
from .serializers import CountryWithCitiesSerializer

class CountryWithCitiesAPIView(APIView):
    def get(self, request):
        countries = Country.objects.prefetch_related('cities').all()
        serializer = CountryWithCitiesSerializer(countries, many=True)
        return Response({"country_data": serializer.data})

