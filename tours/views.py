from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import generics,permissions
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from common.utils import custom_response,get_client_ip,calculate_top_destinations
from .models import Tour,TourAnalytics,TourRating,Wishlist,Destination,ItineraryDay, ItinerarySlot
from .serializers import TourListSerializer,TourDetailSerializer,TourRatingSerializer,CountryCityTourSerializer,TrendingTourSerializer,UpdateTourLocationSerializer
from rest_framework.generics import RetrieveAPIView
from customer_auth.models import CustomerUser
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from customer_auth.authentication import CustomerUserJWTAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from django.db.models import F,Count,Avg,Exists,OuterRef,Value,BooleanField
from rest_framework.permissions import AllowAny
from django.core.cache import cache
from django.db.models import Count, Sum, Avg, Case, When, IntegerField, F
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import ExpressionWrapper, FloatField
from location.models import Country
from decimal import Decimal
from django.shortcuts import get_object_or_404



class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
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
        queryset = Tour.objects.filter(is_active=True) \
            .order_by('-created_at') \
            .prefetch_related('tags') \
            .select_related('country', 'city', 'tour_type')

        user = self.request.user
        if user and user.is_authenticated:
            wishlist_subquery = Wishlist.objects.filter(customer=user, tour=OuterRef('pk'))
            queryset = queryset.annotate(is_liked=Exists(wishlist_subquery))
        else:
            queryset = queryset.annotate(is_liked=Value(False, output_field=BooleanField()))

        return queryset

    @swagger_auto_schema(
        operation_description="Public.",
        tags=["Public APIs"],
        manual_parameters=swagger_params,
        responses={
            200: openapi.Response(
                description="List of tours (paginated or full list)",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "statusCode": openapi.Schema(type=openapi.TYPE_INTEGER),
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
    def get(self, request, *args, **kwargs):  
        return self.list(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        total_count = queryset.count()

        if total_count == 0:
            return custom_response(
                statusCode=status.HTTP_200_OK,
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
                statusCode=status.HTTP_200_OK,
                message="All tours retrieved successfully (no pagination)",
                data={
                    "count": total_count,
                    "results": serializer.data
                }
            )
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            paginated_data["count"] = total_count
            return custom_response(
                statusCode=status.HTTP_200_OK,
                message="Paginated tours retrieved successfully",
                data=paginated_data
            )

        # No pagination fallback
        serializer = self.get_serializer(queryset, many=True)
        return custom_response(
            statusCode=status.HTTP_200_OK,
            message="Tour list retrieved successfully",
            data={
                "count": total_count,
                "results": serializer.data
            }
        )
    
class TourDetailAPIView(RetrieveAPIView):
    authentication_classes = [CustomerUserJWTAuthentication]
    serializer_class = TourDetailSerializer
    lookup_field = 'uuid'  # default is 'pk', you can use 'id' if you prefer
    lookup_url_kwarg = 'tour_uuid'

    def get_queryset(self):
        base_queryset = Tour.objects.all().prefetch_related(
            'tags', 'images', 'itinerary_days', 'age_pricing'
        ).select_related('country', 'city', 'tour_type')

        user = self.request.user
        if user and user.is_authenticated:
            liked_subquery = Wishlist.objects.filter(customer=user, tour=OuterRef('pk'))
            return base_queryset.annotate(is_liked=Exists(liked_subquery))
        else:
            return base_queryset.annotate(is_liked=Value(False, output_field=BooleanField()))
        
    @swagger_auto_schema(
        operation_description="Public.",
        tags=["Public APIs"],
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
                        "statusCode": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            )
        }
    )
    
    def get(self, request, *args, **kwargs):
        lookup_value = self.kwargs.get(self.lookup_url_kwarg)

        try:
            instance = self.get_queryset().get(**{self.lookup_field: lookup_value})
            Tour.objects.filter(pk=instance.pk).update(view_count=F('view_count') + 1)
            instance.refresh_from_db()
        except Tour.DoesNotExist:
            return custom_response(
                statusCode=status.HTTP_404_NOT_FOUND,
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
            statusCode=status.HTTP_200_OK,
            message="Tour details retrieved successfully.",
            data=serializer.data
        )
    
class SubmitRatingView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]

    @swagger_auto_schema(
        operation_description="Submit or update a tour rating",
        request_body=TourRatingSerializer,
        tags=["User Controller"]
    )

    def post(self, request, tour_uuid):
        try:
            tour = Tour.objects.get(uuid=tour_uuid)
        except Tour.DoesNotExist:
            return custom_response(404, "Tour not found", {})

        serializer = TourRatingSerializer(data=request.data)
        if serializer.is_valid():
            rating_obj, created = TourRating.objects.update_or_create(
                tour=tour,
                user=request.user,
                defaults=serializer.validated_data
            )

            # Recalculate average and count
            stats = tour.ratings.aggregate(avg=Avg('rating'), count=Count('rating'))
            tour.rating_average = round(stats['avg'] or 0, 2)
            tour.rating_count = stats['count']
            tour.save()

            return custom_response(
                statusCode=status.HTTP_200_OK,
                message="Rating submitted successfully",
                data=serializer.data
            )

        return custom_response(400, "Invalid data", serializer.errors)


class TrendingToursAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [CustomerUserJWTAuthentication]
    pagination_class = StandardResultsSetPagination 

    @swagger_auto_schema(
        operation_description="Get a list of trending tours (max 20).",
        tags=["Public APIs"],
        responses={
            200: openapi.Response(
                description="Trending tours retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "statusCode": openapi.Schema(type=openapi.TYPE_INTEGER, example=200),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="Trending tours retrieved successfully"),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER, example=607),
                                    "uuid": openapi.Schema(type=openapi.TYPE_STRING, format="uuid", example="6ad5276f-a92a-47d2-9d7e-d873f4a60aa6"),
                                    "title": openapi.Schema(type=openapi.TYPE_STRING, example="Costa Rica Quest"),
                                    "shortDescription": openapi.Schema(type=openapi.TYPE_STRING, example="8-Day Northern Italy Tour of Milan..."),
                                    "tourType": openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        nullable=True,
                                        properties={
                                            "id": openapi.Schema(type=openapi.TYPE_INTEGER, example=1046),
                                            "name": openapi.Schema(type=openapi.TYPE_STRING, example="Beach Adventure")
                                        }
                                    ),
                                    "price": openapi.Schema(type=openapi.TYPE_STRING, example="330.00"),
                                    "currency": openapi.Schema(type=openapi.TYPE_STRING, example="USD"),
                                    "mainImage": openapi.Schema(type=openapi.TYPE_STRING, format="uri", example="/media/tours/main_images/1099ttcgy2021-bilbao-tt-1.webp"),
                                    "isLiked": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                                }
                            )
                        )
                    }
                )
            )
        }
    )
    

    def get(self, request):
        trending_tour_ids = cache.get('trending_tour_ids')
        if not trending_tour_ids:
            trending_tour_ids = list(Tour.objects.filter(trending_score__gt=0)
                                    .order_by('-trending_score')
                                    .values_list('id', flat=True)[:20])
            cache.set('trending_tour_ids', trending_tour_ids, timeout=3600) 

        tours_qs = Tour.objects.filter(id__in=trending_tour_ids).order_by('-trending_score')

        user = request.user
        if user and user.is_authenticated:
            wishlist_subquery = Wishlist.objects.filter(customer=user, tour=OuterRef('pk'))
            tours_qs = tours_qs.annotate(is_liked=Exists(wishlist_subquery))
        else:
            tours_qs = tours_qs.annotate(is_liked=Value(False, output_field=BooleanField()))

       
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(tours_qs, request, view=self)
        serializer = TrendingTourSerializer(page, many=True, context={'request': request})
        
        return custom_response(
            statusCode=status.HTTP_200_OK,
            message="Trending tours retrieved successfully",
            data={
                "results": serializer.data,
                "totalCount": paginator.page.paginator.count,
                "page": paginator.page.number,
                "pageSize": paginator.page.paginator.per_page,
                "totalPages": paginator.page.paginator.num_pages,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link()
            }
        )
    
    

class TopDestinationsAPIView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(
        operation_description="List of top countries with cities and tour counts",
        tags=["Public APIs"],
        manual_parameters=[
        openapi.Parameter(
            name='country_id',
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_INTEGER,
            required=False,
            description='Filter destinations by country ID (from cached top destinations)'
        )
    ],
        responses={
            200: openapi.Response(
                description="Top destinations retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "statusCode": openapi.Schema(type=openapi.TYPE_INTEGER, example=200),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="Top destinations retrieved successfully"),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER, example=732),
                                    "name": openapi.Schema(type=openapi.TYPE_STRING, example="Uzbekistan"),
                                    "destinationSet": openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                "id": openapi.Schema(type=openapi.TYPE_INTEGER, example=13),
                                                "name": openapi.Schema(type=openapi.TYPE_STRING, example="Bukhara, Uzbekistan"),
                                                "city": openapi.Schema(
                                                    type=openapi.TYPE_OBJECT,
                                                    properties={
                                                        "name": openapi.Schema(type=openapi.TYPE_STRING, example="Bukhara"),
                                                        "imageUrl": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI, example="https://api.gostans.com/media/cities/photo-1542314831-068cd1dbfeeb.jpeg")
                                                    }
                                                ),
                                                "tourCount": openapi.Schema(type=openapi.TYPE_INTEGER, example=54)
                                            }
                                        )
                                    )
                                }
                            )
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid country_id",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "statusCode": openapi.Schema(type=openapi.TYPE_INTEGER, example=400),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="Invalid country_id. Must be an integer or 'all'."),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT),  
                            example=[]
                        )
                    }
                )
            )
        }
    )

    
    def get(self, request):
        country_id = request.query_params.get('country_id')
        top_destinations = cache.get("top_destinations")
        # top_destinations = ""
        if not top_destinations:
            destinations = calculate_top_destinations()
            serializer = CountryCityTourSerializer(destinations, many=True, context={'request': request})
            top_destinations = serializer.data
            cache.set("top_destinations", top_destinations, timeout=86400)  # Cache for 1 day
            
        if country_id and country_id != "all":
            try:
                country_id = int(country_id)
                top_destinations = [country for country in top_destinations if country['id'] == country_id]
            except ValueError:
                return custom_response(
                    statusCode=400,
                    message="Invalid country_id. Must be an integer or 'all'.",
                    data=[]
                )
        return custom_response(
            statusCode=200,
            message="Top destinations retrieved successfully",
            data=top_destinations
        )
       
class ToursByDestinationAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [CustomerUserJWTAuthentication]
    pagination_class = StandardResultsSetPagination

    @swagger_auto_schema(
        operation_description="Get tours tagged with top destinations by country and city",
        tags=["Public APIs"],
        manual_parameters=[
            openapi.Parameter(
                name='country_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description='ID of the country'
            ),
            openapi.Parameter(
                name='city_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description='ID of the city'
            )
        ],
        responses={
            200: openapi.Response(
                description="Tours retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "statusCode":openapi.Schema(type=openapi.TYPE_INTEGER, example=200),
                        "message":openapi.Schema(type=openapi.TYPE_STRING,  example="Tours retrieved successfully"),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "results": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            "id": openapi.Schema(type=openapi.TYPE_INTEGER, example=531),
                                            "uuid":openapi.Schema(type=openapi.TYPE_STRING, format="uuid", example="e6d95e29-5994-4638-9d95-d8770ee91e73"),
                                            "title":openapi.Schema(type=openapi.TYPE_STRING, example="Cultural Wonders of Kyoto"),
                                            "shortDescription": openapi.Schema(type=openapi.TYPE_STRING, example="Morning despite concern teach economic red…"),
                                            "tourType":openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True, 
                                                properties={
                                                    "id":   openapi.Schema(type=openapi.TYPE_INTEGER, example=1046),
                                                    "name": openapi.Schema(type=openapi.TYPE_STRING,  example="Beach Adventure")
                                                }
                                            ),
                                            "price": openapi.Schema(type=openapi.TYPE_STRING, example="330.00"),
                                            "currency":openapi.Schema(type=openapi.TYPE_STRING, example="USD"),
                                            "mainImage":openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI, example="http://.../media/tours/..."),
                                            "isLiked": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                                            "cityName": openapi.Schema(type=openapi.TYPE_STRING, example="Almaty"),
                                            "countryName":openapi.Schema(type=openapi.TYPE_STRING, example="Kazakhstan"),
                                        }
                                    )
                                ),
                                "totalCount": openapi.Schema(type=openapi.TYPE_INTEGER, example=123),
                                "page":       openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                "pageSize":   openapi.Schema(type=openapi.TYPE_INTEGER, example=20),
                                "totalPages": openapi.Schema(type=openapi.TYPE_INTEGER, example=7),
                                "next":       openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI, example="http://.../?page=2"),
                                "previous":   openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI, example=None),
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description="Invalid parameters")
        }
    
    )
    def get(self, request):
        country_id = request.query_params.get('country_id')
        city_id = request.query_params.get('city_id')

        if not country_id or not city_id:
            return custom_response(400, "country_id and city_id are required", [])

        try:
            country_id = int(country_id)
            city_id = int(city_id)
        except ValueError:
            return custom_response(400, "Invalid country_id or city_id", [])

        # Get cached top destinations data
        top_destinations = cache.get("top_destinations")
        if not top_destinations:
            return custom_response(400, "Top destinations cache is empty, try again later.", [])

        # Find the matching country in cached data
        country_data = next((c for c in top_destinations if c['id'] == country_id), None)
        if not country_data:
            return custom_response(400, "Country not found in top destinations", [])


        city_destinations = [
            dest for dest in country_data.get('destination_set', [])
            if dest.get('city') and dest['city'].get('id') == city_id
        ]

        if not city_destinations:
            return custom_response(200, "No top destinations found for this city", [])

        # Extract destination IDs
        destination_ids = [dest['id'] for dest in city_destinations]
        user = request.user
        tours_qs = Tour.objects.filter(destination_id__in=destination_ids).order_by('-trending_score')[:50]

        if user and user.is_authenticated:
            wishlist_subquery = Wishlist.objects.filter(customer=user, tour=OuterRef('pk'))
            tours_qs = tours_qs.annotate(is_liked=Exists(wishlist_subquery))
        else:
            tours_qs = tours_qs.annotate(is_liked=Value(False, output_field=BooleanField()))

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(tours_qs, request, view=self)

        serializer = TourListSerializer(page, many=True, context={'request': request})

        return custom_response(
            statusCode=status.HTTP_200_OK,
            message="Tours retrieved successfully",
            data={
                "results": serializer.data,
                "totalCount": paginator.page.paginator.count,
                "page": paginator.page.number,
                "pageSize": paginator.page.paginator.per_page,
                "totalPages": paginator.page.paginator.num_pages,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link()
            }
        )

# class UpdateTourLocationView(APIView):
#     @swagger_auto_schema(
#         operation_description="Update latitude and longitude for one or more tour itinerary days.",
#         tags=["Public APIs"],
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             required=['tour_uuid', 'days'],
#             properties={
#                 "tour_uuid": openapi.Schema(
#                     type=openapi.TYPE_STRING,
#                     format="uuid",
#                     description="UUID of the tour"
#                 ),
#                 "days": openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     description="Dictionary of day numbers mapped to coordinates",
#                     example={
#                         "1": {"latitude": 41.311081, "longitude": 69.240562},
#                         "2": {"latitude": 41.312345, "longitude": 69.241234}
#                     },
#                     additional_properties=openapi.Schema(
#                         type=openapi.TYPE_OBJECT,
#                         properties={
#                             "latitude": openapi.Schema(
#                                 type=openapi.TYPE_NUMBER,
#                                 format="float",
#                                 description="Latitude for the given day"
#                             ),
#                             "longitude": openapi.Schema(
#                                 type=openapi.TYPE_NUMBER,
#                                 format="float",
#                                 description="Longitude for the given day"
#                             ),
#                         },
#                         required=["latitude", "longitude"]
#                     )
#                 )
#             }
#         ),
#         responses={
#             200: openapi.Response(
#                 description="Itineraries updated successfully",
#                 examples={
#                     "application/json": {
#                         "status": 200,
#                         "message": "Itineraries updated successfully for days: [1]"
#                     }
#                 }
#             ),
#             404: openapi.Response(
#                 description="Tour or Itinerary not found",
#                 examples={
#                     "application/json": {
#                         "status": 404,
#                         "message": "Tour not found or itinerary day 2 does not exist"
#                     }
#                 }
#             ),
#             400: openapi.Response(
#                 description="Validation error",
#                 examples={
#                     "application/json": {
#                         "status": 400,
#                         "message": "Validation failed",
#                         "data": {"days": "This field is required."}
#                     }
#                 }
#             )
#         }
#     )
#     def post(self, request):
#         serializer = UpdateTourLocationSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         tour_uuid = serializer.validated_data['tour_uuid']
#         days = serializer.validated_data['days']

#         tour = get_object_or_404(Tour, uuid=tour_uuid)

#         updated_days = []
#         for day_number_str, coords in days.items():
#             day_number = int(day_number_str)
#             itinerary = get_object_or_404(Itinerary, tour=tour, day_number=day_number)
#             itinerary.latitude = coords.get('latitude')
#             itinerary.longitude = coords.get('longitude')
#             itinerary.save()
#             updated_days.append(day_number)

#         return custom_response(
#             statusCode=status.HTTP_200_OK,
#             message="Itineraries updated successfully for days",
           
#         )

class UpdateTourLocationView(APIView):
    @swagger_auto_schema(
        operation_description="Insert or update latitude and longitude for one or more tour itinerary days.",
        tags=["Public APIs"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['tour_uuid', 'days'],
            properties={
                "tour_uuid": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="uuid",
                    description="UUID of the tour"
                ),
                "days": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description="Dictionary of day numbers mapped to coordinates",
                    example={
                        "1": {"latitude": 41.311081, "longitude": 69.240562},
                        "2": {"latitude": 41.312345, "longitude": 69.241234}
                    },
                    additional_properties=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "latitude": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
                            "longitude": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
                        },
                        required=["latitude", "longitude"]
                    )
                )
            }
        ),
    )
    def post(self, request):
        serializer = UpdateTourLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tour_uuid = serializer.validated_data['tour_uuid']
        days = serializer.validated_data['days']

        tour = get_object_or_404(Tour, uuid=tour_uuid)

        inserted_days, updated_days = [], []

        for day_number_str, coords in days.items():
            day_number = int(day_number_str)
            itinerary = get_object_or_404(Itinerary, tour=tour, day_number=day_number)

            if itinerary.latitude is None or itinerary.longitude is None:
                # Insert (first time setting coords)
                itinerary.latitude = coords.get('latitude')
                itinerary.longitude = coords.get('longitude')
                inserted_days.append(day_number)
            else:
                # Always update if already has coords
                itinerary.latitude = coords.get('latitude')
                itinerary.longitude = coords.get('longitude')
                updated_days.append(day_number)

            itinerary.save()

        # Decide response
        if inserted_days and updated_days:
            return custom_response(
                statusCode=status.HTTP_200_OK,
                message=f"Inserted coords for days {inserted_days}, updated coords for days {updated_days}"
            )
        elif inserted_days:
            return custom_response(
                statusCode=status.HTTP_200_OK,
                message=f"Inserted coords successfully for days {inserted_days}"
            )
        elif updated_days:
            return custom_response(
                statusCode=status.HTTP_201_CREATED,
                message=f"Updated coords successfully for days {updated_days}"
            )
        else:
            return custom_response(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="No changes were made."
            )
