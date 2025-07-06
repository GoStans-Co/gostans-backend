
# cart/views.py

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from customer_auth.authentication import CustomerUserJWTAuthentication
from common.utils import custom_response,get_client_ip
from tours.models import Tour,TourAnalytics
from .models import Cart,TourBooking,BookingParticipant,Payment
from tours.serializers import TourListSerializer  
from .serializers import CartItemSerializer,AddToCartSerializer,RemovedCartItemSerializer
from .paypal_client import paypalrestsdk
from rest_framework.views import APIView
from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from django.db.models import F
from paypalrestsdk import Sale, Refund



class CreatePaymentView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]

    @swagger_auto_schema(
        operation_description="Initiate a PayPal payment for a tour booking.",
        tags=["User Controller"],
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
            required=["amount", "tourUuid", "participants"],
            properties={
                "amount": openapi.Schema(type=openapi.TYPE_NUMBER, format="float", description="Total payment amount"),
                "currency": openapi.Schema(type=openapi.TYPE_STRING, description="Currency code (e.g. USD, EUR)", default="USD"),
                "tourUuid": openapi.Schema(type=openapi.TYPE_STRING, format="uuid", description="UUID of the selected tour"),
                "participants": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="List of participants",
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "firstName": openapi.Schema(type=openapi.TYPE_STRING),
                            "lastName": openapi.Schema(type=openapi.TYPE_STRING),
                            "idType": openapi.Schema(type=openapi.TYPE_STRING),
                            "idNumber": openapi.Schema(type=openapi.TYPE_STRING),
                            "dateOfBirth": openapi.Schema(type=openapi.TYPE_STRING, format="date")
                        },
                        required=["firstName", "lastName", "idType", "idNumber", "dateOfBirth"]
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
                            "bookingId": 123,
                            "approvalUrl": "https://paypal.com/approve",
                            "paymentId": "PAY-987654321"
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

        print(request.data)
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

        # print(f"Received tourUuid: {tour_uuid} (type: {type(tour_uuid)})")

        try:        
            tour = Tour.objects.get(uuid=tour_uuid)
        except (Tour.DoesNotExist, ValueError):
            errors["tourUuid"] = "Tour not found or invalid UUID."

        if not participants:
            errors["participants"] = "At least one participant is required."

        if errors:
            return custom_response(
                statusCode=400,
                message="Validation failed",
                data=errors
            )

        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": "http://localhost:5173/payment-success/return",
                "cancel_url": "http://localhost:5173/payment-cancel/return"
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
                    status="PENDING", #this column for booking status ,"pending" as initiating payment 
                    trip_start_date=tour.trip_start_date,
                    trip_end_date=tour.trip_end_date,
                    country=tour.country,
                    city=tour.city
                )
                
                # storing payment history
                Payment.objects.create(
                    booking=booking,
                    payment_id=payment.id,
                    amount=amount,
                    currency=currency,
                    status="PENDING", # this status is for payment status,
                    payment_method="paypal"
                )
                
                for idx, p in enumerate(participants):
                    print(f"Participant {idx+1} data: {p}")
                    missing_fields = [k for k in ("first_name", "last_name", "id_type", "id_number", "date_of_birth") if not p.get(k)]
                    if missing_fields:
                        print(f"Participant {idx+1} missing fields: {missing_fields}")
                        return custom_response(
                            statusCode=400,
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
                        statusCode=200,
                        message="Payment created successfully",
                        data={
                            "bookingId": booking.id,
                            "approvalUrl": link['href'],
                            "paymentId": payment.id
                        }
                    )
        else:
            return custom_response(
                statusCode=400,
                message="Payment creation failed",
                data=payment.error
            )


class ExecutePaymentView(APIView):

    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]

    @swagger_auto_schema(
        operation_description="Execute a PayPal payment after user approval.",
        tags=["User Controller"],
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
                statusCode=400,
                message="Validation failed",
                data=errors
            )

        payment = paypalrestsdk.Payment.find(payment_id)

        if payment.execute({"payer_id": payer_id}):

            try:
                payment_record = Payment.objects.get(payment_id=payment_id)
            except Payment.DoesNotExist:
                return custom_response(404, "Payment record not found", {})

            # Update Payment record
            payment_record.status = "COMPLETED"
            payment_record.payer_id = payer_id

            try:
                sale = payment.transactions[0].related_resources[0].sale
                payment_record.paypal_txn_id = sale.id
            except (IndexError, AttributeError):
                pass
            payment_record.details = payment.to_dict()
            payment_record.save()

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
            # increasing booking count on Tour atomically
            Tour.objects.filter(pk=booking.tour.pk).update(booking_count=F('booking_count') + 1)

            # hnadeling analytics for booking .....
            TourAnalytics.objects.create(
                tour=booking.tour,
                event_type='booking',
                user=booking.customer,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_id=request.session.session_key
            )
            return custom_response(
                statusCode=200,
                message="Payment completed successfully",
                data=payment.to_dict()
            )
        else:
            # Marking booking as cancelled if payment failed....
            try:
                booking = TourBooking.objects.get(payment_id=payment_id)
                booking.status = "Cancelled"
                booking.save()
            except TourBooking.DoesNotExist:
                pass

            return custom_response(
                statusCode=400,
                message="Payment execution failed",
                data=payment.error
            )


class PayPalWebhookView(APIView):
    authentication_classes = []  
    permission_classes = []

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(PayPalWebhookView, self).dispatch(*args, **kwargs)

    @swagger_auto_schema(
        operation_description="PayPal Webhook to handle payment updates (e.g., SALE.COMPLETED, REFUNDED).",
        tags=["💳 Payment Webhooks"],
        responses={
            200: openapi.Response(
                description="Webhook processed successfully",
                examples={
                    "application/json": {
                        "status": 200,
                        "message": "Booking status updated to Booked",
                        "data": {
                            "booking_id": 123,
                            "status": "BOOKED"
                        }
                    }
                }
            ),
            400: openapi.Response(description="Invalid request"),
            404: openapi.Response(description="Booking or payment not found"),
        }
    )

    def post(self, request, *args, **kwargs):
        try:
            event_body = json.loads(request.body)
        except json.JSONDecodeError:
            return custom_response(
                statusCode=400,
                message="Invalid JSON in request body",
                data={}
            )

        event_type = event_body.get("event_type")
        resource = event_body.get("resource", {})

        payment_id = resource.get("parent_payment") or resource.get("id")

        if not payment_id:
            return custom_response(
                statusCode=400,
                message="Payment ID not found in resource",
                data={}
            )

        try:
            booking = TourBooking.objects.get(payment_id=payment_id)
        except TourBooking.DoesNotExist:
            return custom_response(
                statusCode=404,
                message="Booking not found for payment_id",
                data={"payment_id": payment_id}
            )

        try:
            payment_record = Payment.objects.get(payment_id=payment_id)
        except Payment.DoesNotExist:
            return custom_response(404, "Payment record not found", {"payment_id": payment_id})

        # Handle webhook event types
        status_map = {
            "PAYMENT.SALE.COMPLETED": "Booked",
            "PAYMENT.SALE.DENIED": "Denied",
            "PAYMENT.SALE.REFUNDED": "Refunded",
            "PAYMENT.SALE.REVERSED": "Reversed"
        }

        # handeling even in webhook
        if event_type in status_map:
            new_status = status_map[event_type]
            payment_record.status = new_status
            payment_record.save()

            booking =payment_record.booking
            if new_status == "COMPLETED":
                booking.status = "BOOKED" #tour booking done with payment
                booking.save()
                # If booking is now confirmed, increment booking count & log analytics
                Tour.objects.filter(pk=booking.tour.pk).update(booking_count=F('booking_count') + 1)
                TourAnalytics.objects.create(
                    tour=booking.tour,
                    event_type='booking',
                    user=booking.customer,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    session_id=request.session.session_key
                )

            return custom_response(
                statusCode=200,
                message=f"Booking status updated to {status_map[event_type]}",
                data={"booking_id": booking.id, "status": booking.status}
            )

        return custom_response(
            statusCode=200,
            message="Unhandled event type received",
            data={"event_type": event_type}
        )


class CancelBookingView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]

    @swagger_auto_schema(
        operation_description="Cancel a tour booking and refund the payment via PayPal.",
        tags=["User Controller"],
        manual_parameters=[
            openapi.Parameter(
                name='Authorization',
                in_=openapi.IN_HEADER,
                description='JWT Token in format: Bearer <token>',
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["booking_id"],
            properties={
                "booking_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the tour booking to cancel"),
            },
        ),
        responses={
            200: openapi.Response(description="Booking cancelled and refund processed"),
            400: openapi.Response(description="Invalid request or cancellation failed"),
            404: openapi.Response(description="Booking not found"),
        }
    )
    def post(self, request):
        booking_id = request.data.get("booking_id")
        user = request.user

        if not booking_id:
            return custom_response(
                statusCode=400,
                message="booking_id is required",
                data={}
            )

        try:
            booking = TourBooking.objects.get(id=booking_id, customer=user)
        except TourBooking.DoesNotExist:
            return custom_response(
                statusCode=404,
                message="Booking not found for this user",
                data={"booking_id": booking_id}
            )

        # Only allow cancellation if not already cancelled or completed

        if booking.status in ["Cancelled", "Booked"]:
            return custom_response(
                statusCode=400,
                message=f"Booking cannot be cancelled. Current status: {booking.status}",
                data={}
            )

        try:
            payment = Payment.objects.get(booking=booking)
        except Payment.DoesNotExist:
            return custom_response(
                statusCode=404,
                message="Payment record not found for this booking",
                data={"booking_id": booking_id}
            )

        # Refund via PayPal only if payment was completed
        if payment.status != "COMPLETED":
            return custom_response(
                statusCode=400,
                message="Payment not completed, cannot refund",
                data={}
            )

        # Execute PayPal refund
        try:
            # Get sale transaction id from payment record
            sale_id = payment.paypal_txn_id
            if not sale_id:
                return custom_response(
                    statusCode=400,
                    message="No PayPal sale transaction ID found for refund",
                    data={}
                )

            sale = Sale.find(sale_id)
            refund = sale.refund({})

            if not refund.success():
                return custom_response(
                    statusCode=400,
                    message="PayPal refund failed",
                    data=refund.error
                )
        except Exception as e:
            return custom_response(
                statusCode=400,
                message=f"PayPal refund exception: {str(e)}",
                data={}
            )

        # Update booking and payment status inside transaction
        with transaction.atomic():
            booking.status = "Cancelled"
            booking.save()

            payment.status = "Refunded"
            payment.save()

        return custom_response(
            statusCode=200,
            message="Booking cancelled and refund processed successfully",
            data={
                "booking_id": booking.id,
                "payment_id": payment.payment_id,
                "refund_id": refund.id
            }
        )
