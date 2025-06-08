# your_app/factories.py

import factory
from faker import Faker
from factory import  LazyAttribute
import random
from tours.models import *
from partners.models import PartnerProfile
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.core.files import File
import os
from tours.models import Tour
IMAGE_DIR ="media/tours/gallery/"

fake = Faker()

CITIES = ['Paris', 'Tokyo', 'Bali', 'New York', 'Rome', 'Istanbul', 'Barcelona']
COUNTRIES = ['France', 'Japan', 'Indonesia', 'USA', 'Italy', 'Turkey', 'Spain']
TOUR_TITLES = [
    'Romantic Escape in Paris',
    'Cultural Wonders of Kyoto',
    'Bali Beach Retreat',
    'New York City Explorer',
    'Historic Rome Getaway',
    'Istanbul City & Spice Tour',
    'Barcelona Art & Architecture Adventure'
]

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")  # Guarantees uniqueness
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password = factory.PostGenerationMethodCall('set_password', 'password123')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    is_staff = True

class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Country

    name = factory.Faker('country')

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj, created = model_class.objects.get_or_create(name=kwargs.get('name'))
        return obj

class CityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = City

    name = factory.Faker('city')
    country = factory.SubFactory(CountryFactory)


class PartnerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PartnerProfile

    user = factory.SubFactory(UserFactory)
    #phone = factory.Faker('phone_number')
    phone = factory.LazyAttribute(lambda _: fake.phone_number()[:20])
    country = factory.SubFactory(CountryFactory)

    @factory.lazy_attribute
    def city(self):
        return City.objects.filter(country=self.country).order_by('?').first() or CityFactory(country=self.country)

    about = factory.Faker('paragraph')
    tours_added = factory.Faker('random_int', min=1, max=10)


class TourTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TourType

    name = factory.Faker('word')

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj, created = model_class.objects.get_or_create(**kwargs)
        return obj

    
class TourTagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TourTag
        django_get_or_create = ('name',)

    name = factory.Iterator([
        'Family Trip', 'Solo Trip', 'Weekend', 'Adventure', 'Honeymoon', 'Historical',
        'Wildlife', 'Luxury', 'Backpacking', 'Photography'
    ])
    slug = factory.LazyAttribute(lambda o: o.name.lower().replace(' ', '_'))

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj, created = model_class.objects.get_or_create(**kwargs)
        return obj

class TourFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tour

    title = LazyAttribute(lambda x: random.choice(TOUR_TITLES))
    short_description = factory.Faker('text', max_nb_chars=300)
    tour_type = factory.SubFactory(TourTypeFactory)
    duration = factory.Iterator([choice[0] for choice in Tour.DURATION_CHOICES])
    about = factory.Faker('paragraph')
    price = factory.Faker('pydecimal', left_digits=4, right_digits=2, positive=True)
    currency = 'USD'
    group_size = factory.Faker('random_int', min=1, max=30)
    language = ['en']
    age_min = 18
    age_max = 50
    partner = factory.SubFactory(PartnerFactory)
    city = factory.SubFactory(CityFactory)
    country = factory.SubFactory(CountryFactory)
    use_detailed_pricing = True

    @factory.lazy_attribute
    def main_image(self):
        filename = random.choice(os.listdir(IMAGE_DIR))
        path = os.path.join(IMAGE_DIR, filename)
        return File(open(path, 'rb'), name=filename)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create: return
        if extracted:
            for tag in extracted:
                self.tags.add(tag)
        else:
            self.tags.add(TourTagFactory(), TourTagFactory())

class TourPricingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TourPricing

    tour = factory.SubFactory(TourFactory)
    age_category = 'adult'
    price = factory.Faker('pydecimal', left_digits=3, right_digits=2, positive=True)

class TourImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TourImage

    tour = factory.SubFactory(TourFactory)

    @factory.lazy_attribute
    def image(self):
        filename = random.choice(os.listdir(IMAGE_DIR))
        path = os.path.join(IMAGE_DIR, filename)
        return File(open(path, 'rb'), name=filename)


class IncludedItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = IncludedItem

    tour = factory.SubFactory(TourFactory)
    text = factory.Faker('sentence')

class ExcludedItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExcludedItem

    tour = factory.SubFactory(TourFactory)
    text = factory.Faker('sentence')


class ItineraryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Itinerary

    tour = factory.SubFactory(TourFactory)
    day_number = 1  # Will be overridden manually
    day_title = factory.Faker('sentence')
    description = factory.Faker('paragraph')
    accommodation = factory.Faker('company')
    included_meals = factory.Faker('word')
    location_name = factory.Faker('city')
    latitude = factory.Faker('latitude')
    longitude = factory.Faker('longitude')


