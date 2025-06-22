
# cart/views.py

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from customer_auth.authentication import CustomerUserJWTAuthentication
from common.utils import custom_response
from tours.models import Tour
from .models import Cart,TourBooking,BookingParticipant
from tours.serializers import TourListSerializer  
from .serializers import CartItemSerializer,AddToCartSerializer,RemovedCartItemSerializer
from .paypal_client import paypalrestsdk
from rest_framework.views import APIView
from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class AddToCartAPIView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]
    serializer_class = AddToCartSerializer
    queryset = Cart.objects.all()

    @swagger_auto_schema(
        operation_description="Add a tour to the user's cart.",
        manual_parameters=[
            openapi.Parameter(
                name='Authorization',
                in_=openapi.IN_HEADER,
                description='JWT token (Bearer <token>)',
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                name='tour_id',
                in_=openapi.IN_PATH,
                description='UUID of the tour to add to cart',
                type=openapi.TYPE_STRING,
                format='uuid',
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
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        cart_item = result['cart_item']
        created = result['created']

        output_serializer = CartItemSerializer(cart_item)

        return custom_response(
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            message="Tour successfully added to cart." if created else "Tour already in cart. Quantity updated.",
            data=output_serializer.data
        )


class RemoveFromCartAPIView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]
    lookup_url_kwarg = 'tour_uuid'

    @swagger_auto_schema(
        operation_description="Remove a tour from the authenticated user's cart.",
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
                status_code=status.HTTP_200_OK,
                message="Removed from cart",
                data=serializer.data
            )

        return custom_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Item not found in cart",
            data={"tour_uuid": tour.uuid}
        )

class CartListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]
    serializer_class = CartItemSerializer  

    @swagger_auto_schema(
        operation_description="Retrieve all items from the authenticated user's cart.",
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

    def list(self, request, *args, **kwargs):  
        customer = request.user
        cart_items = Cart.objects.filter(customer=customer).select_related('tour')

        if not cart_items.exists():
            return custom_response(
                status_code=status.HTTP_200_OK,
                message="Your cart is empty",
                data=[]
            )

        serializer = self.get_serializer(cart_items, many=True)
        return custom_response(
            status_code=status.HTTP_200_OK,
            message="Cart items retrieved successfully",
            data=serializer.data
        )
    



class CreatePaymentView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]

    @swagger_auto_schema(
        operation_description="Initiate a PayPal payment for a tour booking.",
        manual_parameters=[
            openapi.Parameter(
                name='Authorization',
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description='JWT Token in format: Bearer <token>',
                required=True
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["amount", "tour_uuid", "participants"],
            properties={
                "amount": openapi.Schema(type=openapi.TYPE_NUMBER, format="float", description="Total payment amount"),
                "currency": openapi.Schema(type=openapi.TYPE_STRING, description="Currency code (e.g. USD, EUR)", default="USD"),
                "tour_uuid": openapi.Schema(type=openapi.TYPE_STRING, format="uuid", description="UUID of the selected tour"),
                "participants": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="List of participants",
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "first_name": openapi.Schema(type=openapi.TYPE_STRING),
                            "last_name": openapi.Schema(type=openapi.TYPE_STRING),
                            "id_type": openapi.Schema(type=openapi.TYPE_STRING),
                            "id_number": openapi.Schema(type=openapi.TYPE_STRING),
                            "date_of_birth": openapi.Schema(type=openapi.TYPE_STRING, format="date")
                        },
                        required=["first_name", "last_name", "id_type", "id_number", "date_of_birth"]
                    )
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="Payment created successfully",
                examples={
                    "application/json": {
                        "status": 200,
                        "message": "Payment created successfully",
                        "data": {
                            "booking_id": 123,
                            "approval_url": "https://paypal.com/approve",
                            "payment_id": "PAY-987654321"
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Validation error or PayPal error",
                examples={
                    "application/json": {
                        "status": 400,
                        "message": "Validation failed",
                        "data": {
                            "amount": "Amount must be greater than zero.",
                            "participants": "At least one participant is required."
                        }
                    }
                }
            )
        }
    )

    def post(self, request):
        amount = request.data.get("amount")
        currency = request.data.get("currency", "USD")
        customer = request.user
        tour_uuid = request.data.get("tour_uuid")
        participants = request.data.get("participants", [])

        errors = {}
        if amount is None:
            errors["amount"] = "Amount is required."
        else:
            try:
                amount_val = float(amount)
                if amount_val <= 0:
                    errors["amount"] = "Amount must be greater than zero."
                if round(amount_val, 2) != amount_val:
                    errors["amount"] = "Amount can have up to 2 decimal places."
            except ValueError:
                errors["amount"] = "Amount must be a valid number."

        valid_currencies = {"USD", "EUR", "GBP", "INR", "JPY", "UZS","RUB"}
        if currency and currency.upper() not in valid_currencies:
            errors["currency"] = f"Currency '{currency}' is not supported."

        try:
            tour = Tour.objects.get(uuid=tour_uuid)
        except (Tour.DoesNotExist, ValueError):
            errors["tour_uuid"] = "Tour not found or invalid UUID."

        if not participants:
            errors["participants"] = "At least one participant is required."

        if errors:
            return custom_response(
                status_code=400,
                message="Validation failed",
                data=errors
            )

        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": "https://xplore-asia.web.app/payment-success",
                "cancel_url": "https://xplore-asia.web.app/payment-cancel"
            },
            "transactions": [{
                "amount": {"total": f"{amount}", "currency": currency},
                "description": "Tour Booking Payment"
            }]
        })

        if payment.create():
            with transaction.atomic():
                # Save booking in DB
                booking = TourBooking.objects.create(
                    customer=customer,
                    partner=tour.partner,
                    tour=tour,
                    payment_id=payment.id,
                    amount=amount,
                    currency=currency,
                    status="PENDING",
                    trip_start_date=tour.trip_start_date,
                    trip_end_date=tour.trip_end_date,
                    country=tour.country,
                    city=tour.city
                )

                for idx, p in enumerate(participants):
                    print(f"Participant {idx+1} data: {p}")
                    missing_fields = [k for k in ("first_name", "last_name", "id_type", "id_number", "date_of_birth") if not p.get(k)]
                    if missing_fields:
                        print(f"Participant {idx+1} missing fields: {missing_fields}")
                        return custom_response(
                            status_code=400,
                            message=f"Participant {idx + 1} is missing fields: {', '.join(missing_fields)}",
                            data=p
                        )
                    BookingParticipant.objects.create(
                        booking=booking,
                        first_name=p["first_name"],
                        last_name=p["last_name"],
                        id_type=p["id_type"],
                        id_number=p["id_number"],
                        date_of_birth=p["date_of_birth"]
                    )
                    print(f"Participant {idx+1} saved")

            for link in payment['links']:
                if link['rel'] == 'approval_url':
                    return custom_response(
                        status_code=200,
                        message="Payment created successfully",
                        data={
                            "booking_id": booking.id,
                            "approval_url": link['href'],
                            "payment_id": payment.id
                        }
                    )
        else:
            return custom_response(
                status_code=400,
                message="Payment creation failed",
                data=payment.error
            )


class ExecutePaymentView(APIView):

    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]

    @swagger_auto_schema(
        operation_description="Execute a PayPal payment after user approval.",
        manual_parameters=[
            openapi.Parameter(
                name='Authorization',
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description='JWT Token in format: Bearer <token>',
                required=True
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["paymentId", "PayerID"],
            properties={
                "paymentId": openapi.Schema(type=openapi.TYPE_STRING, description="PayPal payment ID"),
                "PayerID": openapi.Schema(type=openapi.TYPE_STRING, description="PayPal payer ID from redirect URL")
            }
        ),
        responses={
            200: openapi.Response(
                description="Payment executed successfully",
                examples={
                    "application/json": {
                        "status": 200,
                        "message": "Payment completed successfully",
                        "data": {
                            "id": "PAY-123456789",
                            "state": "approved",
                            "payer": {
                                "payment_method": "paypal",
                                "status": "VERIFIED"
                            },
                            # Other PayPal response data...
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Validation failed or execution failed",
                examples={
                    "application/json": {
                        "status": 400,
                        "message": "Validation failed",
                        "data": {
                            "paymentId": "This field is required.",
                            "PayerID": "This field is required."
                        }
                    }
                }
            ),
            404: openapi.Response(
                description="Booking not found",
                examples={
                    "application/json": {
                        "status": 404,
                        "message": "Booking not found",
                        "data": {}
                    }
                }
            )
        }
    )

    def post(self, request):
        payment_id = request.data.get("paymentId")
        payer_id = request.data.get("PayerID")

        errors = {}
        if not payment_id:
            errors["paymentId"] = "This field is required."
        if not payer_id:
            errors["PayerID"] = "This field is required."

        if errors:
            return custom_response(
                status_code=400,
                message="Validation failed",
                data=errors
            )

        payment = paypalrestsdk.Payment.find(payment_id)

        if payment.execute({"payer_id": payer_id}):
            # Find corresponding booking
            try:
                booking = TourBooking.objects.get(payment_id=payment_id)
            except TourBooking.DoesNotExist:
                return custom_response(404, "Booking not found", {})

            # Update booking status
            booking.status = "Booked"  # or "Complete", depending on your app's logic
            booking.payer_id = payer_id

            # Optionally save PayPal sale transaction id if available
            try:
                sale = payment.transactions[0].related_resources[0].sale
                booking.paypal_txn_id = sale.id
            except (IndexError, AttributeError):
                pass

            booking.save()

            return custom_response(
                status_code=200,
                message="Payment completed successfully",
                data=payment.to_dict()
            )
        else:
            try:
                booking = TourBooking.objects.get(payment_id=payment_id)
                booking.status = "Cancelled"
                booking.save()
            except TourBooking.DoesNotExist:
                pass

            return custom_response(
                status_code=400,
                message="Payment execution failed",
                data=payment.error
            )
