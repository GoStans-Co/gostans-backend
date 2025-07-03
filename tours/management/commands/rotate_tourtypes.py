from django.core.management.base import BaseCommand
from tours.models import TourType


class Command(BaseCommand):
    help = 'Rotates TourType names across all records with unique values, preserving IDs'

    def handle(self, *args, **kwargs):
        base_names = [
            "Adventure", "Cultural", "Wildlife", "Beach", "Historical",
            "Luxury", "Backpacking", "Cruise", "Eco Tour", "Hiking"
        ]

        tour_types = TourType.objects.order_by('id')
        count = 0

        for index, tour_type in enumerate(tour_types):
            base_name = base_names[index % len(base_names)]
            new_name = f"{base_name} {index + 1}"  # make name unique
            if tour_type.name != new_name:
                tour_type.name = new_name
                tour_type.save(update_fields=["name"])
                count += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Updated {count} TourType records with unique rotated names."
        ))
