from rest_framework import serializers
from .models import Tour, TourTag, TourType,TourImage,ItineraryDay, ItinerarySlot,TourPricing,Wishlist,ExcludedItem,IncludedItem,TourRating,Destination
from location.models import Country,City

class TourTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = TourTag
        fields = ['id', 'name', 'slug']

class TourTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TourType
        fields = ['id', 'name']


class TourListSerializer(serializers.ModelSerializer):
    tour_type = TourTypeSerializer(read_only=True)
    is_liked = serializers.SerializerMethodField()
    city_name = serializers.CharField(source='city.name', read_only=True)
    country_name = serializers.CharField(source='city.country.name', read_only=True)

    class Meta:
        model = Tour
        fields = ['id','uuid', 'title', 'short_description', 'tour_type', 'price', 'currency', 'main_image','is_liked','city_name','country_name','trip_start_date','trip_end_date']

    def get_is_liked(self, obj):
        return getattr(obj, 'is_liked', False)
    
class TourImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TourImage
        fields = ['id', 'image']

class LocationSerializer(serializers.Serializer):
    name = serializers.CharField()
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, allow_null=True)

class ItinerarySlotSerializer(serializers.ModelSerializer):
    locationNames = serializers.SerializerMethodField()

    class Meta:
        model = ItinerarySlot
        fields = ['start_time', 'end_time', 'title', 'description', 'locationNames']

    def get_locationNames(self, obj):
        if obj.location_name:
            return [{
                "name": obj.location_name,
                "latitude": obj.latitude,
                "longitude": obj.longitude
            }]
        return []

class ItineraryDaySerializer(serializers.ModelSerializer):
    slots = ItinerarySlotSerializer(many=True, read_only=True)

    class Meta:
        model = ItineraryDay
        fields = ['day_number', 'day_title', 'description', 'slots']


# class ItinerarySerializer(serializers.ModelSerializer):
#     locationNames = serializers.SerializerMethodField()

#     class Meta:
#         model = Itinerary
#         fields = [
#             'day_number', 'day_title', 'description', 'accommodation', 
#             'included_meals', 'locationNames'
#         ]
#     def get_locationNames(self, obj):
#         locations = []
#         if obj.location_name:
#             # Split by comma in case multiple locations are provided: "Samarkand, Bukhara"
#             for loc in [name.strip() for name in obj.location_name.split(",") if name.strip()]:
#                 locations.append({
#                     "name": loc,
#                     "latitude": obj.latitude,
#                     "longitude": obj.longitude,
#                 })
#         return locations


class TourPricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TourPricing
        fields = ['age_category', 'price']


class ExcludedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExcludedItem
        fields = ['text']

    def to_representation(self, instance):
        # Split comma-separated text into multiple items
        items = [t.strip() for t in instance.text.split(',') if t.strip()]
        return [{'text': t} for t in items]

class IncludedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncludedItem
        fields = ['text']

    def to_representation(self, instance):
        # Split comma-separated text into multiple items
        items = [t.strip() for t in instance.text.split(',') if t.strip()]
        return [{'text': t} for t in items]

class TourDetailSerializer(serializers.ModelSerializer):
    images = TourImageSerializer(many=True, read_only=True)
    # itineraries = ItinerarySerializer(many=True, read_only=True)
    itineraries = ItineraryDaySerializer(many=True, read_only=True, source='itinerary_days')
    agepricing = TourPricingSerializer(many=True, read_only=True)
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field='slug')
    excludedItem = ExcludedItemSerializer(source='excluded_items',many=True, read_only=True)
    includedItem = IncludedItemSerializer(source='included_items', many=True, read_only=True)
    tour_type = serializers.StringRelatedField()
    country = serializers.StringRelatedField()
    city = serializers.StringRelatedField()
    is_liked = serializers.SerializerMethodField()
    duration = serializers.ReadOnlyField(source='duration_display')

    class Meta:
        model = Tour
        fields = [
            'id','uuid', 'title', 'short_description', 'tour_type', 'duration', 'about', 'price', 'currency',
            'trip_start_date', 'trip_end_date', 'country', 'city', 'group_size', 'language',
            'age_min', 'age_max', 'partner', 'tags', 'main_image', 'created_at',
            'images', 'itineraries', 'agepricing','excludedItem','includedItem','is_liked'
        ] 
    def get_is_liked(self, obj):
        return getattr(obj, 'is_liked', False)       


class WishlistAddSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wishlist
        fields = ['tour']

    def create(self, validated_data):
        customer = self.context['request'].user
        tour = validated_data['tour']
        wishlist, created = Wishlist.objects.get_or_create(customer=customer, tour=tour)
        return wishlist

class WishlistTourSerializer(serializers.ModelSerializer):
    uuid = serializers.CharField(source='tour.uuid')
    title = serializers.CharField(source='tour.title')
    tour_type = serializers.StringRelatedField(source='tour.tour_type')
    main_image = serializers.ImageField(source='tour.main_image')
    
    class Meta:
        model = Wishlist
        fields = ['id','uuid','title','tour_type','main_image']


class RemovedWishlistItemSerializer(serializers.Serializer):
    tour_uuid = serializers.UUIDField()
    message = serializers.CharField()


class TourRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TourRating
        fields = ['rating', 'review']


class CitySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = ['id','name', 'image_url']

    def get_image_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None
    
class DestinationSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    tour_count = serializers.SerializerMethodField()

    class Meta:
        model = Destination
        fields = ['id', 'name', 'city', 'tour_count']

    def get_tour_count(self, obj):
        return getattr(obj, 'tour_count', 0)


class CountryCityTourSerializer(serializers.ModelSerializer):
    destination_set = DestinationSerializer(many=True, read_only=True)

    class Meta:
        model = Country
        fields = ['id', 'name', 'destination_set']


class TrendingTourSerializer(serializers.ModelSerializer):
    tour_type = TourTypeSerializer(read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Tour
        fields = [
            'id',
            'uuid',
            'title',
            'short_description',
            'tour_type',
            'price',
            'currency',
            'main_image',
            'is_liked',
        ]

    def get_is_liked(self, obj):
        return getattr(obj, 'is_liked', False)


class UpdateTourLocationSerializer(serializers.Serializer):
    tour_uuid = serializers.UUIDField()
    days = serializers.DictField(
        child=serializers.DictField(
            child=serializers.DecimalField(max_digits=9, decimal_places=6)
        ),
        required=True
    )