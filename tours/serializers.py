from rest_framework import serializers
from .models import Tour, TourTag, TourType,TourImage,Itinerary,TourPricing,Wishlist,ExcludedItem,IncludedItem

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
    
    class Meta:
        model = Tour
        fields = ['id','uuid', 'title', 'short_description', 'tour_type', 'price', 'currency', 'main_image']

class TourImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TourImage
        fields = ['id', 'image']

class ItinerarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Itinerary
        fields = [
            'day_number', 'day_title', 'description', 'accommodation', 
            'included_meals', 'location_name', 'latitude', 'longitude'
        ]


class TourPricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TourPricing
        fields = ['age_category', 'price']


class ExcludedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExcludedItem
        fields = ['text']

class IncludedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncludedItem
        fields = ['text']



class TourDetailSerializer(serializers.ModelSerializer):
    images = TourImageSerializer(many=True, read_only=True)
    itineraries = ItinerarySerializer(many=True, read_only=True)
    age_pricing = TourPricingSerializer(many=True, read_only=True)
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field='slug')
    excluded=ExcludedItemSerializer(source='excluded_items',many=True, read_only=True)
    IncludedItem=IncludedItemSerializer(source='excluded_items',many=True, read_only=True)
    tour_type = serializers.StringRelatedField()
    country = serializers.StringRelatedField()
    city = serializers.StringRelatedField()

    class Meta:
        model = Tour
        fields = [
            'id','uuid', 'title', 'short_description', 'tour_type', 'duration', 'about', 'price', 'currency',
            'trip_start_date', 'trip_end_date', 'country', 'city', 'group_size', 'language',
            'age_min', 'age_max', 'partner', 'tags', 'main_image', 'created_at',
            'images', 'itineraries', 'age_pricing','excluded','IncludedItem'
        ]        


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