from django.db import models
from location.models import Country, City  # Replace with actual location models
from django.contrib.auth.models import User
from multiselectfield import MultiSelectField
from smart_selects.db_fields import ChainedForeignKey

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


class Tour(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('ru', 'Russian'),
        ('uz', 'Uzbek'),
        ('ko', 'Korean'),
    ]

    DURATION_CHOICES = [(f'{i} day', f'{i} Day{"s" if i > 1 else ""}') for i in range(1, 8)]

    title = models.CharField(max_length=255)
    short_description = models.TextField(max_length=300)
    tour_type = models.ForeignKey(TourType, on_delete=models.SET_NULL, null=True)
    duration = models.CharField(max_length=10, choices=DURATION_CHOICES)
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

    def __str__(self):
        return self.title

    @property
    def tag_list(self):
        return list(self.tags.values_list('slug', flat=True))

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

class Itinerary(models.Model):
    tour = models.ForeignKey(Tour, related_name='itineraries', on_delete=models.CASCADE)
    day_number = models.PositiveIntegerField()
    day_title = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    accommodation = models.CharField(max_length=255, blank=True)
    included_meals = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('tour', 'day_number')
        ordering = ['day_number']

    def __str__(self):
        return f"Day {self.day_number} - {self.day_title or 'Itinerary'}"