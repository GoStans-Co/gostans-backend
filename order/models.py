from django.db import models
from customer_auth.models import CustomerUser
from tours.models import Tour
from location.models import Country, City  # Replace with actual location models



class Cart(models.Model):
    customer = models.ForeignKey(CustomerUser, on_delete=models.CASCADE, related_name='cart_items')
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='cart_entries')
    quantity = models.PositiveIntegerField(default=1)  # Add this
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('customer', 'tour')  # Prevent duplicates

    def __str__(self):
        return f"{self.customer} - {self.tour} (x{self.quantity})"


class TourBooking(models.Model):
    STATUS_CHOICES = [
        ("Waiting", "waiting"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    ]

    id = models.AutoField(primary_key=True)
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name="bookings")
    customer = models.ForeignKey('customer_auth.CustomerUser', on_delete=models.CASCADE, related_name="bookings")
    partner = models.ForeignKey('partners.PartnerProfile', on_delete=models.CASCADE, related_name="bookings")

    payment_id = models.CharField(max_length=100, unique=True)
    payer_id = models.CharField(max_length=100, blank=True, null=True)
    paypal_txn_id = models.CharField(max_length=100, blank=True, null=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    trip_start_date = models.DateField(null=True, blank=True)
    trip_end_date = models.DateField(null=True, blank=True)

    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.customer.email} booked {self.tour.title} ({self.status})"


class BookingParticipant(models.Model):
    ID_TYPE_CHOICES = [
        ('passport', 'Passport'),
        ('national_id', 'National ID'),
        ('driver_license', 'Driver’s License'),
        # Add more if needed
    ]

    booking = models.ForeignKey('TourBooking', on_delete=models.CASCADE, related_name='participants')

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    id_type = models.CharField(max_length=50, choices=ID_TYPE_CHOICES)
    id_number = models.CharField(max_length=100)
    date_of_birth = models.DateField()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.booking.tour.title})"
