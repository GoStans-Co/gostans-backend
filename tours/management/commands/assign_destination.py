from django.core.management.base import BaseCommand
from tours.models import Tour

class Command(BaseCommand):
    help = "Assign destinations to existing tours based on country and city"

    def handle(self, *args, **kwargs):
        tours = Tour.objects.filter(destination__isnull=True, country__isnull=False, city__isnull=False)
        count = 0

        for tour in tours:
            tour.save(update_fields=['destination'])  # triggers save() logic
            count += 1

        self.stdout.write(self.style.SUCCESS(f" Assigned destinations to {count} existing tours."))
        
