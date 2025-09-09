import uuid
import requests
from django.conf import settings
from django.db import models
from location.models import Country, City  # Replace with actual location models
from django.contrib.auth.models import User
from multiselectfield import MultiSelectField
from smart_selects.db_fields import ChainedForeignKey
from common.utils import get_coordinates
from customer_auth.models import CustomerUser

# destination logic 
class Destination(models.Model):
    name = models.CharField(max_length=255)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    image_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.city.name}, {self.country.name})"

    class Meta:
        unique_together = ('name', 'city', 'country')

class TourType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class TourTag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    #tours = models.ManyToManyField('Tour', related_name='tags', blank=True)

    def __str__(self):
        return self.name

class TourPricing(models.Model):
    AGE_CATEGORY_CHOICES = [
        ('adult', 'Adult'),
        ('child', 'Child'),
        ('infant', 'Infant'),
    ]

    tour = models.ForeignKey(
        'Tour',
        on_delete=models.CASCADE,
        related_name='age_pricing'
    )
    age_category = models.CharField(max_length=10, choices=AGE_CATEGORY_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('tour', 'age_category')

    def __str__(self):
        return f"{self.tour.title} - {self.age_category}: {self.price}"

class Tour(models.Model):
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    use_detailed_pricing = models.BooleanField(
        default=False,
        help_text="Enable age-specific pricing (e.g., adult, child)"
    )

    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('ru', 'Russian'),
        ('uz', 'Uzbek'),
        ('ko', 'Korean'),
    ]
        
    title = models.CharField(max_length=255)
    short_description = models.TextField(max_length=300)
    tour_type = models.ForeignKey(TourType, on_delete=models.SET_NULL, null=True)
    # duration = models.CharField(max_length=10, choices=DURATION_CHOICES)
    # duration = models.PositiveIntegerField(help_text="Enter number of days for the tour")
    duration_days = models.PositiveIntegerField(
        null=True, blank=True, help_text="Enter number of days for the tour"
    )
    duration_hours = models.PositiveIntegerField(
        null=True, blank=True, help_text="Additional hours for short tours or half-day tours"
    )
    about = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(
        max_length=10,
        choices=[('USD', 'USD ($)'), ('EUR', 'EUR (€)'), ('KRW', 'KRW (₩)')],
        default='USD'
    )
    trip_start_date = models.DateField(null=True, blank=True)
    trip_end_date = models.DateField(null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)
    #city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True)
    city = ChainedForeignKey(
        City,
        chained_field="country",
        chained_model_field="country",
        show_all=False,
        auto_choose=True,
        sort=True,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    group_size = models.PositiveIntegerField()
    language = MultiSelectField(choices=LANGUAGE_CHOICES,max_length=20)
    age_min = models.PositiveIntegerField(default=18)
    age_max = models.PositiveIntegerField(default=99)
    partner = models.ForeignKey('partners.PartnerProfile', on_delete=models.CASCADE, related_name='tours')
    tags = models.ManyToManyField('TourTag', related_name='tours', blank=True)
    main_image = models.ImageField(upload_to='tours/main_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Analytics & Trending Fields
    view_count = models.PositiveIntegerField(default=0, help_text="Total number of times this tour has been viewed")
    booking_count = models.PositiveIntegerField(default=0, help_text="Total number of bookings for this tour")
    rating_average = models.DecimalField(max_digits=3, decimal_places=2, default=0.0, help_text="Average rating out of 5")
    rating_count = models.PositiveIntegerField(default=0, help_text="Total number of ratings received")
    last_booked_at = models.DateTimeField(null=True, blank=True, help_text="When this tour was last booked")
    trending_score = models.FloatField(default=0.0, help_text="Calculated score for trending algorithm")
    destination = models.ForeignKey(Destination, on_delete=models.SET_NULL, null=True, blank=True, related_name='tours')

    is_active = models.BooleanField(
        default=True,
        help_text="Mark tour as active or inactive"
    )

    def get_price(self, age_category='adult'):
        if self.use_detailed_pricing:
            pricing = self.age_pricing.filter(age_category=age_category).first()
            return pricing.price if pricing else None
        return self.price

    def save(self, *args, **kwargs):
        # Auto-assign destination if not already set
        if self.country and self.city:
            from tours.models import Destination  # local import to avoid circular import
            destination_name = f"{self.city.name}, {self.country.name}"
            destination, _ = Destination.objects.get_or_create(
                country=self.country,
                city=self.city,
                defaults={'name': destination_name}
            )
            self.destination = destination

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def tag_list(self):
        return list(self.tags.values_list('slug', flat=True))

    @property
    def duration_display(self):
        parts = []
        if self.duration_days:
            parts.append(f"{self.duration_days} Day{'s' if self.duration_days > 1 else ''}")
        if self.duration_hours:
            parts.append(f"{self.duration_hours} Hour{'s' if self.duration_hours > 1 else ''}")
        return " + ".join(parts) if parts else "N/A"


class TourImage(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='tours/gallery/')

    def __str__(self):
        return f"Image for {self.tour.title}"


class IncludedItem(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='included_items')
    text = models.CharField(max_length=255)

    def __str__(self):
        return f"Included: {self.text}"

class ExcludedItem(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='excluded_items')
    text = models.CharField(max_length=255)

    def __str__(self):
        return f"Excluded: {self.text}"


class ItineraryDay(models.Model):
    tour = models.ForeignKey(
        Tour, related_name="itinerary_days", on_delete=models.CASCADE
    )
    day_number = models.PositiveIntegerField()
    day_title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    accommodation = models.CharField(
        max_length=255, blank=True, null=True, help_text="E.g. Hotel name or place of stay"
    )
    included_meals = models.CharField(
        blank=True, null=True, help_text="E.g. Breakfast, Lunch, Dinner"
    )
    location_name = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        unique_together = ("tour", "day_number")
        ordering = ["day_number"]

    def __str__(self):
        return f"Day {self.day_number} - {self.day_title or 'Itinerary'}"


class ItinerarySlot(models.Model):
    day = models.ForeignKey(
        ItineraryDay, related_name="slots", on_delete=models.CASCADE
    )
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    included_meals = models.CharField(
        blank=True, null=True, help_text="E.g. Breakfast, Lunch, Dinner"
    )
    location_name = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.title or 'Activity'} ({self.start_time} - {self.end_time})"


class Wishlist(models.Model):
    customer = models.ForeignKey('customer_auth.CustomerUser', on_delete=models.CASCADE, related_name='wishlists')
    tour = models.ForeignKey('tours.Tour', on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('customer', 'tour')

    def __str__(self):
        return f"{self.customer.email} - {self.tour.title}"

class TourAnalytics(models.Model):
    EVENT_TYPES = [
        ('view', 'View'),
        ('booking', 'Booking'),
        ('search', 'Search'),
        ('wishlist_add', 'Wishlist Add'),
        ('engagement', 'Engagement'),
    ]

    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='analytics')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    user = models.ForeignKey(CustomerUser, null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.event_type} on {self.tour.title} at {self.timestamp}"

class TourRating(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(CustomerUser, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()  # from 1 to 5
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tour', 'user')  # Optional: prevent duplicate ratings per user
