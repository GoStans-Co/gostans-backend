from rest_framework import generics,permissions
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from common.utils import custom_response
from .models import Wishlist,Tour
from .serializers import TourListSerializer,TourDetailSerializer,WishlistAddSerializer, WishlistTourSerializer
from rest_framework.generics import RetrieveAPIView
from customer_auth.models import CustomerUser
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from customer_auth.authentication import CustomerUserJWTAuthentication
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView


class WishlistPagination(PageNumberPagination):
    page_size = 5  # Default 5 items
    page_size_query_param = 'page_size'  # Optional: allow clients to override
    max_page_size = 10 

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'  # Allow client to change page size
    max_page_size = 20


class TourListAPIView(generics.ListAPIView):
    authentication_classes = [CustomerUserJWTAuthentication]
    queryset = Tour.objects.all().prefetch_related('tags').select_related('country', 'city', 'tour_type')
    serializer_class = TourListSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]

    # Filtering exact matches by these fields
    filterset_fields = {
        'country__id': ['exact'],
        'city__id': ['exact'],
        'tour_type__id': ['exact'],
        'tags__slug': ['exact'],
    }

    # Search by title, short_description, or about fields (partial match)
    search_fields = ['title', 'short_description', 'about']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        total_count = queryset.count()

        if total_count == 0:
            return custom_response(
                status_code=status.HTTP_200_OK,
                message="No tours available.",
                data={
                    "count": 0,
                    "next": None,
                    "previous": None,
                    "results": []
                }
            )

        # Handle ?all=true to return everything
        if request.query_params.get("all") == "true":
            serializer = self.get_serializer(queryset, many=True)
            return custom_response(
                status_code=status.HTTP_200_OK,
                message="All tours retrieved successfully (no pagination)",
                data={
                    "count": total_count,
                    "results": serializer.data
                }
            )

        # Handle pagination
        try:
            page = self.paginate_queryset(queryset)
        except NotFound:
            return custom_response(
                status_code=404,
                message="Invalid page number.",
                data={}
            )

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            # Inject `count` manually into paginated response
            paginated_data['count'] = total_count
            return custom_response(
                status_code=status.HTTP_200_OK,
                message="Paginated tours retrieved successfully",
                data=paginated_data
            )

        # Fallback: no pagination
        serializer = self.get_serializer(queryset, many=True)
        return custom_response(
            status_code=status.HTTP_200_OK,
            message="Tour list retrieved successfully",
            data={
                "count": total_count,
                "results": serializer.data
            }
        )


class TourDetailAPIView(RetrieveAPIView):
    queryset = Tour.objects.all().prefetch_related(
        'tags', 'images', 'itineraries', 'age_pricing'
    ).select_related('country', 'city', 'tour_type')
    serializer_class = TourDetailSerializer
    lookup_field = 'uuid'  # default is 'pk', you can use 'id' if you prefer
    lookup_url_kwarg = 'tour_uuid'

    def retrieve(self, request, *args, **kwargs):
        lookup_value = self.kwargs.get(self.lookup_url_kwarg)

        try:
            instance = self.get_queryset().get(**{self.lookup_field: lookup_value})
        except Tour.DoesNotExist:
            return custom_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Tour not found.",
                data={}
            )

        serializer = self.get_serializer(instance)
        return custom_response(
            status_code=status.HTTP_200_OK,
            message="Tour details retrieved successfully.",
            data=serializer.data
        )


class WishlistAddAPIView(APIView):

    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]
    lookup_field = 'uuid'
    lookup_url_kwarg = 'tour_uuid'

    def post(self, request, tour_uuid):
        customer = request.user  # Assumes user is authenticated
        tour = get_object_or_404(Tour, uuid=tour_uuid)

        wishlist, created = Wishlist.objects.get_or_create(customer=customer, tour=tour)

        if created:
            return custom_response(
                status_code=status.HTTP_201_CREATED,
                message="Added to wishlist",
                data={"tour_uuid": tour.uuid}
            )
        else:
            return custom_response(
                status_code=status.HTTP_200_OK,
                message="Already in wishlist",
                data={"tour_uuid": tour.uuid}
            )


class WishlistListAPIView(generics.ListAPIView):
    serializer_class = WishlistTourSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]
    pagination_class = WishlistPagination

    def get_queryset(self):
        return Wishlist.objects.filter(customer=self.request.user).select_related('tour')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        if not queryset.exists():
            return custom_response(
                status_code=status.HTTP_200_OK,
                message="Your wishlist is empty.",
                data={
                    "count": 0,
                    "next": None,
                    "previous": None,
                    "results": []
                }
            )

        try:
            page = self.paginate_queryset(queryset)
        except NotFound:
            return custom_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Invalid page number.",
                data={}
            )

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            return custom_response(
                status_code=status.HTTP_200_OK,
                message="Wishlist retrieved successfully",
                data=paginated_data
            )

        serializer = self.get_serializer(queryset, many=True)
        return custom_response(
            status_code=status.HTTP_200_OK,
            message="Wishlist retrieved successfully",
            data={"results": serializer.data}
        )
