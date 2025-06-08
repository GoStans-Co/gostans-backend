#management/commands/seed_data.py
from django.core.management.base import BaseCommand
from random import randint

from tours.factories import (
    TourFactory, IncludedItemFactory, ExcludedItemFactory, ItineraryFactory,
    TourPricingFactory,TourImageFactory
)

class Command(BaseCommand):
    help = "Seed sample tour data"

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=5)
        parser.add_argument('--env', type=str, default='local')

    def handle(self, *args, **options):
        count = options['count']
        env = options['env']

        if env == 'prod':
            self.stdout.write(self.style.ERROR("Seeding not allowed in production"))
            return

        if env == 'local':
            from tours.models import TourTag, TourType, Country,TourPricing,IncludedItem,ExcludedItem,Itinerary,Tour
            TourPricing.objects.all().delete()
            IncludedItem.objects.all().delete()
            ExcludedItem.objects.all().delete()
            Itinerary.objects.all().delete()
            Tour.objects.all().delete()


            # deleting base table
            TourTag.objects.all().delete()
            TourType.objects.all().delete()
            Country.objects.all().delete()

        for _ in range(count):
            tour = TourFactory()

            # Related objects
            for _ in range(3):
                IncludedItemFactory(tour=tour)
                ExcludedItemFactory(tour=tour)
            
            for age in ['adult', 'child']:
                TourPricingFactory(tour=tour, age_category=age)

            # Random number of itinerary days (1 to 7)
            days = randint(1, 7)
            for day in range(1, days + 1):
                ItineraryFactory(tour=tour, day_number=day)
            
            for _ in range(3):
                TourImageFactory(tour=tour)
                
        self.stdout.write(self.style.SUCCESS(f" Seeded {count} tours with full relations"))
