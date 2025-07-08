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
        return ""
    
    class Meta:
        verbose_name = "Participant"
        verbose_name_plural = "Participants"

class Payment(models.Model):
    booking = models.ForeignKey(TourBooking, on_delete=models.CASCADE, related_name="payments")
    payment_id = models.CharField(max_length=255, unique=True)  # paypal payment id or gateway txn id
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    status = models.CharField(max_length=50)  # e.g., 'PENDING', 'COMPLETED', 'FAILED', 'REFUNDED'
    payment_method = models.CharField(max_length=50, default='paypal')
    payer_id = models.CharField(max_length=255, blank=True, null=True)  # PayPal payer ID
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    details = models.JSONField(blank=True, null=True)  # To store raw payment gateway response for audit

    def __str__(self):
        return f"Payment {self.payment_id} for Booking {self.booking.id}"


class CardholderInfo(models.Model):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="cardholder_info")
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)

    address1 = models.CharField(max_length=255)
    locality = models.CharField(max_length=100)  # City
    administrative_area = models.CharField(max_length=100)  # State
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=2)  # ISO country code like 'US', 'IN'

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.payment.payment_id}"


class SavedCard(models.Model):
    user = models.ForeignKey(CustomerUser, on_delete=models.CASCADE, related_name="saved_cards")
    customer_profile_id = models.CharField(max_length=255)  # from CyberSource
    payment_token_id = models.CharField(max_length=255, unique=True)  # paymentInstrumentId
    card_type = models.CharField(max_length=20)
    last4 = models.CharField(max_length=4)
    expiry_month = models.CharField(max_length=2)
    expiry_year = models.CharField(max_length=4)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class FailedCardSaveLog(models.Model):
    user = models.ForeignKey(CustomerUser, on_delete=models.CASCADE)
    booking = models.ForeignKey(TourBooking, on_delete=models.CASCADE)
    card_data = models.JSONField()  # Mask sensitive info in prod!
    error_message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
