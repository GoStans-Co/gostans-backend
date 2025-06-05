
# cart/views.py

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from customer_auth.authentication import CustomerUserJWTAuthentication
from common.utils import custom_response
from tours.models import Tour
from .models import Cart
from tours.serializers import TourListSerializer  
from .serializers import CartItemSerializer


class AddToCartAPIView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]

    def post(self, request):
        customer = request.user
        tour_uuid = request.data.get("tour_uuid")
        quantity = request.data.get("quantity", 1)

        # Validate tour_uuid
        if not tour_uuid:
            return custom_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Tour UUID is required."
            )

        # Validate quantity
        try:
            quantity = int(quantity)
            if quantity < 1:
                raise ValueError
        except (ValueError, TypeError):
            return custom_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid quantity. It must be a positive integer."
            )

        tour = get_object_or_404(Tour, uuid=tour_uuid)

        # Check if cart item already exists
        cart_item, created = Cart.objects.get_or_create(customer=customer, tour=tour)

        if created:
            # New item added to cart
            cart_item.quantity = quantity
            cart_item.save()
            return custom_response(
                status_code=status.HTTP_201_CREATED,
                message="Tour added to cart",
                data={
                    "tour_uuid": str(tour.uuid),
                    "quantity": cart_item.quantity
                }
            )
        else:
            # Tour already in cart – update quantity
            cart_item.quantity += quantity  # or set to quantity directly
            cart_item.save()
            return custom_response(
                status_code=status.HTTP_200_OK,
                message="Tour already in cart. Quantity updated.",
                data={
                    "tour_uuid": str(tour.uuid),
                    "quantity": cart_item.quantity
                }
            )

class RemoveFromCartAPIView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]
    lookup_url_kwarg = 'tour_uuid'

    def delete(self, request, tour_uuid):
        customer = request.user
        tour = get_object_or_404(Tour, uuid=tour_uuid)

        cart_item = Cart.objects.filter(customer=customer, tour=tour).first()
        if cart_item:
            cart_item.delete()
            return custom_response(
                status_code=status.HTTP_200_OK,
                message="Removed from cart",
                data={"tour_uuid": tour.uuid}
            )
        return custom_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Item not found in cart",
            data={"tour_uuid": tour.uuid}
        )

class CartListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]

    def get(self, request):
        customer = request.user
        cart_items = Cart.objects.filter(customer=customer).select_related('tour')

        if not cart_items.exists():
            return custom_response(
                status_code=status.HTTP_200_OK,
                message="Your cart is empty",
                data=[]
            )

        serialized = CartItemSerializer(cart_items, many=True)

        return custom_response(
            status_code=status.HTTP_200_OK,
            message="Cart items retrieved successfully",
            data=serialized.data
        )
