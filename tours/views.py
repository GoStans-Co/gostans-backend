from rest_framework import generics,permissions
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from common.utils import custom_response,get_client_ip
from .models import Wishlist,Tour,TourAnalytics
from .serializers import TourListSerializer,TourDetailSerializer,WishlistAddSerializer, WishlistTourSerializer,RemovedWishlistItemSerializer
from rest_framework.generics import RetrieveAPIView
from customer_auth.models import CustomerUser
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from customer_auth.authentication import CustomerUserJWTAuthentication
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import F




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
    
    swagger_params = [
        openapi.Parameter('country__id', openapi.IN_QUERY, description="Filter by Country ID", type=openapi.TYPE_INTEGER),
        openapi.Parameter('city__id', openapi.IN_QUERY, description="Filter by City ID", type=openapi.TYPE_INTEGER),
        openapi.Parameter('tour_type__id', openapi.IN_QUERY, description="Filter by Tour Type ID", type=openapi.TYPE_INTEGER),
        openapi.Parameter('tags__slug', openapi.IN_QUERY, description="Filter by Tour Tag Slug", type=openapi.TYPE_STRING),
        openapi.Parameter('search', openapi.IN_QUERY, description="Search by title, short_description, or about", type=openapi.TYPE_STRING),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number for pagination", type=openapi.TYPE_INTEGER),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Page size for pagination", type=openapi.TYPE_INTEGER),
        openapi.Parameter('all', openapi.IN_QUERY, description="Set to true to retrieve all tours without pagination", type=openapi.TYPE_BOOLEAN),
    ]

    def get_queryset(self):
        return Tour.objects.all() \
            .order_by('-created_at') \
            .prefetch_related('tags') \
            .select_related('country', 'city', 'tour_type')

    @swagger_auto_schema(
        manual_parameters=swagger_params,
        responses={
            200: openapi.Response(
                description="List of tours (paginated or full list)",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "status_code": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "count": openapi.Schema(type=openapi.TYPE_INTEGER, description="Total number of tours"),
                                "next": openapi.Schema(type=openapi.TYPE_STRING, description="URL of next page", nullable=True),
                                "previous": openapi.Schema(type=openapi.TYPE_STRING, description="URL of previous page", nullable=True),
                                "results": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                            },
                            description="Paginated list of tours or full list if ?all=true"
                        ),
                    }
                )
            )
        }
    )

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
    authentication_classes = [CustomerUserJWTAuthentication]

    queryset = Tour.objects.all().prefetch_related(
        'tags', 'images', 'itineraries', 'age_pricing'
    ).select_related('country', 'city', 'tour_type')
    serializer_class = TourDetailSerializer
    lookup_field = 'uuid'  # default is 'pk', you can use 'id' if you prefer
    lookup_url_kwarg = 'tour_uuid'

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'tour_uuid',
                openapi.IN_PATH,
                description="UUID of the Tour to retrieve",
                type=openapi.TYPE_STRING,
                format='uuid',
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Tour details retrieved successfully",
                schema=TourDetailSerializer()
            ),
            404: openapi.Response(
                description="Tour not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "status_code": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            )
        }
    )
    
    def retrieve(self, request, *args, **kwargs):
        lookup_value = self.kwargs.get(self.lookup_url_kwarg)

        try:
            instance = self.get_queryset().get(**{self.lookup_field: lookup_value})
            # Increment view_count atomically
            Tour.objects.filter(pk=instance.pk).update(view_count=F('view_count') + 1)
            instance.refresh_from_db()
        except Tour.DoesNotExist:
            return custom_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Tour not found.",
                data={}
            )

        TourAnalytics.objects.create(
            tour=instance,
            event_type='view',
            user=request.user if request.user.is_authenticated else None,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            session_id=request.session.session_key
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

    @swagger_auto_schema(
        operation_description="Add a tour to the authenticated user's wishlist.",
        manual_parameters=[
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                description="JWT Token in format: Bearer <token>",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                name="tour_uuid",
                in_=openapi.IN_PATH,
                description="UUID of the tour to add to wishlist",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            201: openapi.Response(
                description="Tour added to wishlist",
                examples={
                    "application/json": {
                        "status": 201,
                        "message": "Added to wishlist",
                        "data": {
                            "tour_uuid": "2f6b89bb-8309-4151-afda-0ec1d039878a"
                        }
                    }
                }
            ),
            200: openapi.Response(
                description="Tour already in wishlist",
                examples={
                    "application/json": {
                        "status": 200,
                        "message": "Already in wishlist",
                        "data": {
                            "tour_uuid": "2f6b89bb-8309-4151-afda-0ec1d039878a"
                        }
                    }
                }
            ),
            401: openapi.Response(
                description="Unauthorized",
                examples={
                    "application/json": {
                        "detail": "Authentication credentials were not provided."
                    }
                }
            ),
            404: openapi.Response(
                description="Tour not found",
                examples={
                    "application/json": {
                        "detail": "Not found."
                    }
                }
            )
        }
    )

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

    @swagger_auto_schema(
        operation_description="Retrieve the authenticated user's wishlist.",
        manual_parameters=[
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="JWT token in format: Bearer <token>",
                required=True
            ),
            openapi.Parameter(
                name="page",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="Page number for paginated results"
            )
        ],
        responses={
            200: openapi.Response(
                description="Wishlist retrieved or empty",
                examples={
                    "application/json": {
                        "status": 200,
                        "message": "Wishlist retrieved successfully",
                        "data": {
                            "count": 1,
                            "next": None,
                            "previous": None,
                            "results": [
                                {
                                    "uuid": "2f6b89bb-8309-4151-afda-0ec1d039878a",
                                    "tour": {
                                        "title": "Jeju Island Adventure",
                                        "price": 150.0,
                                        "duration": "3 days"
                                    }
                                }
                            ]
                        }
                    }
                }
            ),
            404: openapi.Response(
                description="Invalid page number",
                examples={
                    "application/json": {
                        "status": 404,
                        "message": "Invalid page number.",
                        "data": {}
                    }
                }
            )
        }
    )

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



class RemoveFromWishlistAPIView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]

    @swagger_auto_schema(
        operation_description="Remove a tour from the authenticated user's wishlist.",
        manual_parameters=[
            openapi.Parameter(
                name='Authorization',
                in_=openapi.IN_HEADER,
                description='JWT token (Bearer <token>)',
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                name='tour_uuid',
                in_=openapi.IN_PATH,
                description='UUID of the tour to remove from wishlist/Add "all" to remove all',
                type=openapi.TYPE_STRING,
                format='uuid',
                required=True,
            )
           
        ],
        responses={
            200: openapi.Response(
                description="Removed from wishlist",
                examples={
                    "application/json": {
                        "status": 200,
                        "message": "Removed from wishlist",
                        "data": {
                            "tour_uuid": "2f6b89bb-8309-4151-afda-0ec1d039878a",
                            "message": "Removed from wishlist"
                        }
                    }
                }
            ),
            404: openapi.Response(
                description="Item not found in wishlist",
                examples={
                    "application/json": {
                        "status": 404,
                        "message": "Item not found in wishlist",
                        "data": {
                            "tour_uuid": "2f6b89bb-8309-4151-afda-0ec1d039878a"
                        }
                    }
                }
            ),
            401: openapi.Response(
                description="Unauthorized",
                examples={
                    "application/json": {
                        "detail": "Authentication credentials were not provided."
                    }
                }
            )
        }
    )

    def delete(self, request, tour_uuid):
        customer = request.user
        if not tour_uuid:
            return custom_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="tour_uuid is required",
                data={}
            )

        if str(tour_uuid) == "all":
            deleted_count, _ = Wishlist.objects.filter(customer=customer).delete()
            return custom_response(
                status_code=status.HTTP_200_OK,
                message="All wishlist items removed",
                data={"deleted_count": deleted_count}
            )

        tour = get_object_or_404(Tour, uuid=tour_uuid)

        wishlist_item = Wishlist.objects.filter(customer=customer, tour=tour).first()
        if wishlist_item:
            wishlist_item.delete()

            serializer = RemovedWishlistItemSerializer({
                "tour_uuid": tour.uuid,
                "message": "Removed from wishlist"
            })

            return custom_response(
                status_code=status.HTTP_200_OK,
                message="Removed from wishlist",
                data=serializer.data
            )

        return custom_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Item not found in wishlist",
            data={"tour_uuid": tour_uuid}
        )
