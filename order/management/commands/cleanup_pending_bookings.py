from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from order.models import TourBooking,Payment

class Command(BaseCommand):
    help = 'Cancel pending bookings and mark payments as failed if not completed within 30 minutes.'

    def handle(self, *args, **kwargs):
        cutoff_time = timezone.now() - timedelta(minutes=30)

        stale_bookings = TourBooking.objects.filter(
            status='PENDING',
            created_at__lt=cutoff_time
        )

        count = stale_bookings.count()

        for booking in stale_bookings:
            booking.status = 'CANCELLED'
            booking.save()

            # Updating related payment(s)
            Payment.objects.filter(booking=booking).update(status='FAILED')

        self.stdout.write(self.style.SUCCESS(f" Cleaned up {count} stale bookings."))
