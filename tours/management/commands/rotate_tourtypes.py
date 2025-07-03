from django.core.management.base import BaseCommand
from tours.models import TourType


class Command(BaseCommand):
    help = 'Rotates TourType names using a predefined list across all records without changing IDs'

    def handle(self, *args, **kwargs):
        names = [
            "Adventure", "Cultural", "Wildlife", "Beach", "Historical",
            "Luxury", "Backpacking", "Cruise", "Eco Tour", "Hiking"
        ]

        tour_types = TourType.objects.order_by('id')
        count = 0

        for index, tour_type in enumerate(tour_types):
            new_name = names[index % len(names)]
            if tour_type.name != new_name:
                tour_type.name = new_name
                tour_type.save(update_fields=["name"])
                count += 1

        self.stdout.write(self.style.SUCCESS(
            f" Updated {count} TourType records with rotated names."
        ))
