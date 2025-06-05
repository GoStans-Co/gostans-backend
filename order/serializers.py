from rest_framework import serializers
from .models import Cart
from tours.models import Tour

class TourSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Tour
        fields = ['uuid', 'title', 'price', 'main_image', 'tour_type', 'about']  # remove 'quantity'


class CartItemSerializer(serializers.ModelSerializer):
    tour = TourSummarySerializer(read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'tour', 'quantity', 'added_at']