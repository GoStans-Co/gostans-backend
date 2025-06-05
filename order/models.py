from django.db import models
from customer_auth.models import CustomerUser
from tours.models import Tour


class Cart(models.Model):
    customer = models.ForeignKey(CustomerUser, on_delete=models.CASCADE, related_name='cart_items')
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='cart_entries')
    quantity = models.PositiveIntegerField(default=1)  # Add this
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('customer', 'tour')  # Prevent duplicates

    def __str__(self):
        return f"{self.customer} - {self.tour} (x{self.quantity})"
