
# cart/views.py

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from customer_auth.authentication import CustomerUserJWTAuthentication
from common.utils import custom_response
from tours.models import Tour
from .models import Cart
from tours.serializers import TourListSerializer  
from .serializers import CartItemSerializer,AddToCartSerializer,RemovedCartItemSerializer

class AddToCartAPIView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomerUserJWTAuthentication]
    serializer_class = AddToCartSerializer
    queryset = Cart.objects.all()

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
