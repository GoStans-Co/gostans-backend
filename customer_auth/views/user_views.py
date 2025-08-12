from django.utils.timezone import now
from datetime import date
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import status,generics,permissions,parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from ..serializers import CustomerUserSerializer,CustomerUserProfileSerializer
from rest_framework.permissions import IsAuthenticated
from customer_auth.authentication import CustomerUserJWTAuthentication
from django.contrib.auth import get_user_model
from rest_framework import status
from google.oauth2 import id_token
from google.auth.transport import requests
from django.utils.crypto import get_random_string
from common.utils import custom_response,generate_otp,get_client_ip
from django.shortcuts import get_object_or_404
from tours.models import Wishlist,Tour,TourAnalytics
from tours.serializers import WishlistTourSerializer,RemovedWishlistItemSerializer
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import NotFound
from order.models import Cart,TourBooking
from order.serializers import AddToCartSerializer,CartItemSerializer,RemovedCartItemSerializer,TourBookingSerializer,BookingParticipantSerializer,PaymentSerializer


class WishlistPagination(PageNumberPagination):
    page_size = 5  # Default 5 items
    page_size_query_param = 'page_size'  # Optional: allow clients to override
    max_page_size = 10 


# Update API - Update user details

class CustomerUserUpdateView(generics.UpdateAPIView):
    serializer_class = CustomerUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user  # Required for UpdateAPIView to know what to update

    @swagger_auto_schema(
        operation_description="Update profile of the authenticated user.",
        tags=["User Controller"],
        request_body=CustomerUserSerializer,
        manual_parameters=[
            openapi.Parameter(
                'Authorization',
                openapi.IN_HEADER,
                description="JWT token (Bearer <token>)",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Profile updated successfully",
                examples={
                    "application/json": {
                        "status": 200,
                        "message": "Profile updated successfully",
                        "data": {
                            "id": 1,
                            "email": "user@example.com",
                            "name": "Updated Name",
                            "phone": "9876543210"
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
                            "phone": ["Phone number must be exactly 10 digits."]
                        }
                    }
                }
            )
        }
    )
   
    def put(self, request):
        user = request.user
        serializer = CustomerUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return custom_response(
                statusCode=status.HTTP_200_OK,
                message="Profile updated successfully",
                data=serializer.data
            )
        return custom_response(
            statusCode=status.HTTP_400_BAD_REQUEST,
            message="Validation failed",
            data=serializer.errors
        )

    
#api for fetching user profile
class CustomerUserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]
    
    @swagger_auto_schema(
        operation_description="Fetch the authenticated user's profile.",
        tags=["User Controller"],
        manual_parameters=[
            openapi.Parameter(
                'Authorization',
                openapi.IN_HEADER,
                description="JWT token (Bearer <access_token>)",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Profile fetched successfully",
                examples={
                    "application/json": {
                        "status": 200,
                        "message": "Profile detail fetched successfully",
                        "data": {
                            "id": 1,
                            "email": "user@example.com",
                            "name": "John Doe",
                            "phone": "+821012345678",
                            "image": None,
                            "date_joined": "2025-06-22 17:01",
                            "updated_at": "2025-06-22 17:01",
                            "is_verified": True,
                            "bookings": {
                                "all": [
                                    {
                                        "id": 3,
                                        "uuid": "6ad5276f-a92a-47d2-9d7e-d873f4a60aa6",
                                        "tourTitle": "Costa Rica Quest",
                                        "tourType": "solo",
                                        "mainImage": "/media/tours/main_images/1099ttcgy2021-bilbao-tt-1_gcxXVOW.webp",
                                        "amount": "660.00",
                                        "currency": "USD",
                                        "status": "COMPLETED",
                                        "tripStartDate": "2025-08-30",
                                        "tripEndDate": "2026-06-27",
                                        "createdAt": "2025-06-20T09:08:17.829470Z"
                                    }
                                ],
                                "upcoming": [
                                    {
                                        "id": 3,
                                        "uuid": "6ad5276f-a92a-47d2-9d7e-d873f4a60aa6",
                                        "tourTitle": "Costa Rica Quest",
                                        "tourType": "solo",
                                        "mainImage": "/media/tours/main_images/1099ttcgy2021-bilbao-tt-1_gcxXVOW.webp",
                                        "amount": "660.00",
                                        "currency": "USD",
                                        "status": "COMPLETED",
                                        "tripStartDate": "2025-08-30",
                                        "tripEndDate": "2026-06-27",
                                        "createdAt": "2025-06-20T09:08:17.829470Z"
                                    }
                                ],
                                "completed": [{
                                        "id": 3,
                                        "uuid": "6ad5276f-a92a-47d2-9d7e-d873f4a60aa6",
                                        "tourTitle": "Costa Rica Quest",
                                        "tourType": "solo",
                                        "mainImage": "/media/tours/main_images/1099ttcgy2021-bilbao-tt-1_gcxXVOW.webp",
                                        "amount": "660.00",
                                        "currency": "USD",
                                        "status": "COMPLETED",
                                        "tripStartDate": "2025-08-30",
                                        "tripEndDate": "2026-06-27",
                                        "createdAt": "2025-06-20T09:08:17.829470Z"
                                    }]
                            },
                            "wishlists": [
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

    def get(self, request):
        user = request.user
        today = date.today()

        all_bookings = TourBooking.objects.filter(customer=user).select_related('tour')

        upcoming_bookings = all_bookings.filter(
            status="COMPLETED",
            trip_start_date__gt=today
        )

        completed_bookings = all_bookings.filter(
            status="COMPLETED",
            trip_end_date__lte=today
        )

        profile_data = CustomerUserProfileSerializer(user).data
        profile_data["bookings"] = {
            "all": TourBookingSerializer(all_bookings, many=True).data,
            "upcoming": TourBookingSerializer(upcoming_bookings, many=True).data,
            "completed": TourBookingSerializer(completed_bookings, many=True).data
        }
        return custom_response(
            statusCode=status.HTTP_200_OK,
            data=profile_data,
            message="Profile detail fetched sucessfully"
        )

#api for update image
class CustomerUserImageUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    @swagger_auto_schema(
        operation_description="update profile image for authenticated user.",
        tags=["User Controller"],
        manual_parameters=[
            openapi.Parameter(
                name='Authorization',
                in_=openapi.IN_HEADER,
                description="JWT token (Bearer <token>)",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                name='image',
                in_=openapi.IN_FORM,
                description='Image file to upload',
                type=openapi.TYPE_FILE,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Image uploaded successfully",
                examples={
                    "application/json": {
                        "status": 200,
                        "message": "Image updated successfully",
                        "data": {}
                    }
                }
            ),
            400: openapi.Response(
                description="Image not provided",
                examples={
                    "application/json": {
                        "status": 400,
                        "message": "No image provided",
                        "data": {}
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

    def patch(self, request):
        user = request.user
        print(request.user)
        image = request.FILES.get('image')

        if not image:
            return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)

        user.image = image
        user.save()

        return custom_response(
            statusCode=status.HTTP_200_OK,
            message="Image updated successfully",
            data={}
        )
 

class WishlistAddAPIView(APIView):

    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]
    lookup_field = 'uuid'
    lookup_url_kwarg = 'tour_uuid'

    @swagger_auto_schema(
        operation_description="Add a tour to the authenticated user's wishlist.",
        tags=["User Controller"],
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

        wishlist_entry = Wishlist.objects.filter(customer=customer, tour=tour)

        if wishlist_entry.exists():
            wishlist_entry.delete()
            return custom_response(
                statusCode=200,
                message="Removed from wishlist",
                data={"tour_uuid": tour.uuid, "is_wishlisted": False}
            )
        else:
            Wishlist.objects.create(customer=customer, tour=tour)
            TourAnalytics.objects.create(
                tour=tour,
                event_type='wishlist_add',
                user=request.user if request.user.is_authenticated else None,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_id=request.session.session_key
            )
            return custom_response(
                statusCode=201,
                message="Added to wishlist",
                data={"tour_uuid": tour.uuid, "is_wishlisted": True}
            )


class WishlistListAPIView(generics.ListAPIView):
    serializer_class = WishlistTourSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]
    pagination_class = WishlistPagination

    def get_queryset(self):
        return Wishlist.objects.filter(customer=self.request.user).select_related('tour')


    @swagger_auto_schema(
        operation_description="Retrieve the authenticated user's wishlist.",
        tags=["User Controller"],
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

   
    def get(self, request, *args, **kwargs):
        """
        Override `get()` to hook into Swagger.
        Internally still calls `.list()`.
        """
        return self.list(request, *args, **kwargs)
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        if not queryset.exists():
            return custom_response(
                statusCode=status.HTTP_200_OK,
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
                statusCode=status.HTTP_404_NOT_FOUND,
                message="Invalid page number.",
                data={}
            )

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            return custom_response(
                statusCode=status.HTTP_200_OK,
                message="Wishlist retrieved successfully",
                data=paginated_data
            )

        serializer = self.get_serializer(queryset, many=True)
        return custom_response(
            statusCode=status.HTTP_200_OK,
            message="Wishlist retrieved successfully",
            data={"results": serializer.data}
        )



class RemoveFromWishlistAPIView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]

    @swagger_auto_schema(
        operation_description="Remove a tour from the authenticated user's wishlist.",
        tags=["User Controller"],
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
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="tour_uuid is required",
                data={}
            )

        if str(tour_uuid) == "all":
            deleted_count, _ = Wishlist.objects.filter(customer=customer).delete()
            return custom_response(
                statusCode=status.HTTP_200_OK,
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
                statusCode=status.HTTP_200_OK,
                message="Removed from wishlist",
                data=serializer.data
            )

        return custom_response(
            statusCode=status.HTTP_404_NOT_FOUND,
            message="Item not found in wishlist",
            data={"tour_uuid": tour_uuid}
        )


# cart related api

class AddToCartAPIView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]
    serializer_class = AddToCartSerializer
    queryset = Cart.objects.all()

    @swagger_auto_schema(
        operation_description="Add a tour to the user's cart.",
        tags=["User Controller"],
        manual_parameters=[
            openapi.Parameter(
                name='Authorization',
                in_=openapi.IN_HEADER,
                description='JWT token (Bearer <token>)',
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        request_body=AddToCartSerializer,
        responses={
            201: openapi.Response(
                description="Tour added to cart successfully",
                schema=CartItemSerializer,
                # examples...
            ),
            200: openapi.Response(
                description="Tour already in cart, quantity updated",
                schema=CartItemSerializer,
                # examples...
            ),
            400: openapi.Response(description="Validation error"),
            401: openapi.Response(description="Unauthorized"),
        }
    )
    
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        cart_item = result['cart_item']
        created = result['created']

        output_serializer = CartItemSerializer(cart_item)

        return custom_response(
            statusCode=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            message="Tour successfully added to cart." if created else "Tour already in cart. Quantity updated.",
            data=output_serializer.data
        )

class RemoveFromCartAPIView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]
    lookup_url_kwarg = 'tour_uuid'

    @swagger_auto_schema(
        operation_description="Remove a tour from the user's cart.",
        tags=["User Controller"],
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
                description='UUID of the tour to remove from cart',
                type=openapi.TYPE_STRING,
                format='uuid',
                required=True,
            )
        ],
        responses={
            200: openapi.Response(
                description="Removed from cart",
                examples={
                    "application/json": {
                        "status": 200,
                        "message": "Removed from cart",
                        "data": {
                            "tour_uuid": "2f6b89bb-8309-4151-afda-0ec1d039878a",
                            "message": "Removed from cart"
                        }
                    }
                }
            ),
            404: openapi.Response(
                description="Item not found in cart",
                examples={
                    "application/json": {
                        "status": 404,
                        "message": "Item not found in cart",
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
        tour = get_object_or_404(Tour, uuid=tour_uuid)

        cart_item = Cart.objects.filter(customer=customer, tour=tour).first()
        if cart_item:
            cart_item.delete()

            serializer = RemovedCartItemSerializer({
                "tour_uuid": tour.uuid,
                "message": "Removed from cart"
            })

            return custom_response(
                statusCode=status.HTTP_200_OK,
                message="Removed from cart",
                data=serializer.data
            )

        return custom_response(
            statusCode=status.HTTP_404_NOT_FOUND,
            message="Item not found in cart",
            data={"tour_uuid": tour.uuid}
        )


class CartListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]
    serializer_class = CartItemSerializer  
    

    @swagger_auto_schema(
        operation_description="Retrieve all items from the authenticated user's cart.",
        tags=["User Controller"],
        manual_parameters=[
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                description="JWT token (Bearer <token>)",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Cart items retrieved or cart is empty",
                examples={
                    "application/json": {
                        "status": 200,
                        "message": "Cart items retrieved successfully",
                        "data": [
                            {
                                "id": 1,
                                "tour": {
                                    "id": 12,
                                    "title": "Jeju Island Tour",
                                    "price": 150
                                },
                                "quantity": 2
                            },
                            {
                                "id": 2,
                                "tour": {
                                    "id": 9,
                                    "title": "Seoul Food Crawl",
                                    "price": 80
                                },
                                "quantity": 1
                            }
                        ]
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

    def get(self, request, *args, **kwargs):  
        return self.list(request, *args, **kwargs)
    
    def list(self, request, *args, **kwargs):  
        customer = request.user
        cart_items = Cart.objects.filter(customer=customer).select_related('tour')

        if not cart_items.exists():
            return custom_response(
                statusCode=status.HTTP_200_OK,
                message="Your cart is empty",
                data=[]
            )

        serializer = self.get_serializer(cart_items, many=True)
        return custom_response(
            statusCode=status.HTTP_200_OK,
            message="Cart items retrieved successfully",
            data=serializer.data
        )
    


# api for order api detail
class OrderDetailView(APIView):

    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]

    booking_id_param = openapi.Parameter(
        'booking_id', openapi.IN_BODY, description="Booking ID to fetch details", type=openapi.TYPE_INTEGER, required=True
    )

    @swagger_auto_schema(
        operation_description="Get detailed order info by booking ID",
        tags=["Order"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'booking_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Booking ID'),
            },
            required=['booking_id']
        ),
        responses={
            200: openapi.Response(
                description="Order detail fetched successfully",
                examples={
                    "application/json": {
                        "statusCode": 200,
                        "message": "Order detail fetched successfully",
                        "data": {
                            "id": 5,
                            "uuid": "60806051-d3d6-4555-86d5-13652401791f",
                            "tourTitle": "Cultural Wonders of Kyoto",
                            "tourType": None,
                            "mainImage": "/media/tours/main_images/view-madrid-spain-1_CLNF3pD_lkNl6wn_Oct96My.webp",
                            "amount": "7079.84",
                            "currency": "USD",
                            "status": "CANCELLED",
                            "tripStartDate": None,
                            "tripEndDate": None,
                            "createdAt": "2025-07-06T12:16:31.237630Z",
                            "payments": [
                                {
                                    "id": 2,
                                    "paymentId": "PAYID-NBVGSIA70691654T7165104W",
                                    "amount": "7079.84",
                                    "currency": "USD",
                                    "status": "FAILED",
                                    "paymentMethod": "paypal",
                                    "payerId": None,
                                    "createdAt": "2025-07-06T12:16:31.263787Z",
                                    "updatedAt": "2025-07-06T12:16:31.263847Z",
                                    "details": None,
                                    "booking": 5
                                }
                            ],
                            "participants": [
                                {
                                    "firstName": "Alice",
                                    "lastName": "Smith",
                                    "idType": "Passport",
                                    "idNumber": "A12345678",
                                    "dateOfBirth": "1990-05-15"
                                },
                                {
                                    "firstName": "Bob",
                                    "lastName": "Johnson",
                                    "idType": "National ID",
                                    "idNumber": "ID987654321",
                                    "dateOfBirth": "1985-10-30"
                                }
                            ]
                        }
                    }
                }
            ),
            404: openapi.Response(description="Booking not found"),
            400: openapi.Response(description="Bad request")
        }
    )
    def post(self, request):
        booking_id = request.data.get('booking_id')
        if not booking_id:
            return custom_response(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message="booking_id is required",
                data={}
            )

        booking = get_object_or_404(
            TourBooking.objects.select_related('tour', 'customer', 'partner', 'country', 'city')
            .prefetch_related('participants', 'payments'),
            id=booking_id,
            customer=request.user
        )

        serializer = TourBookingSerializer(booking)
        return custom_response(
            statusCode=status.HTTP_200_OK,
            data=serializer.data,
            message="Order detail fetched successfully"
        )

       
