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


class AddToCartSerializer(serializers.ModelSerializer):
    tour_uuid = serializers.UUIDField(write_only=True)
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = Cart
        fields = ['tour_uuid', 'quantity']  

    def create(self, validated_data):
        user = self.context['request'].user
        tour_uuid = validated_data.pop('tour_uuid')
        quantity = validated_data.get('quantity', 1)
        tour = Tour.objects.get(uuid=tour_uuid)

        cart_item, created = Cart.objects.get_or_create(customer=user, tour=tour)
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        else:
            cart_item.quantity = quantity
            cart_item.save()

        return {'cart_item': cart_item, 'created': created}

class RemovedCartItemSerializer(serializers.Serializer):
    tour_uuid = serializers.UUIDField()
    message = serializers.CharField()
