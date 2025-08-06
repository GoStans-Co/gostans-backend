from rest_framework import serializers
from .models import Cart,Payment,CardholderInfo,SavedCard
from tours.models import Tour
from .models import TourBooking, BookingParticipant
from tours.models import Tour

class TourSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Tour
        fields = ['uuid', 'title', 'price', 'main_image', 'tour_type','duration','short_description']  # remove 'quantity'


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


class BookingParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingParticipant
        fields = ['first_name', 'last_name', 'id_type', 'id_number', 'date_of_birth']


class TourBookingCreateSerializer(serializers.ModelSerializer):
    participants = BookingParticipantSerializer(many=True)

    class Meta:
        model = TourBooking
        fields = [
            'tour', 'payment_id', 'amount', 'currency', 'trip_start_date',
            'trip_end_date', 'participants'
        ]

    def validate(self, data):
        tour = data.get("tour")
        if not tour:
            raise serializers.ValidationError("Tour is required.")
        return data

    def create(self, validated_data):
        participants_data = validated_data.pop('participants')
        customer = self.context['request'].user
        tour = validated_data['tour']

        booking = TourBooking.objects.create(
            customer=customer,
            partner=tour.partner,
            **validated_data
        )

        for participant in participants_data:
            BookingParticipant.objects.create(booking=booking, **participant)

        return booking
    

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'


class TourBookingSerializer(serializers.ModelSerializer):
    tour_title = serializers.CharField(source='tour.title', read_only=True)
    main_image = serializers.ImageField(source='tour.main_image', read_only=True)
    tour_type = serializers.CharField(source='tour.tour_type', read_only=True)
    uuid = serializers.UUIDField(source='tour.uuid', read_only=True)

    class Meta:
        model = TourBooking
        fields = [
            'id',
            'uuid',
            'tour_title',
            'tour_type',
            'main_image',
            'amount',
            'currency',
            'status',
            'trip_start_date',
            'trip_end_date',
            'created_at'
        ]

class CardholderInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardholderInfo
        fields = '__all__'

class SavedCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedCard
        fields = '__all__'