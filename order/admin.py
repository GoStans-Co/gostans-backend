from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import TourBooking, BookingParticipant
from django.utils.safestring import mark_safe
from django.urls import reverse

class BookingParticipantInline(admin.TabularInline):
    model = BookingParticipant
    extra = 0
    readonly_fields = ("first_name", "last_name", "id_type", "id_number", "date_of_birth")



@admin.register(TourBooking)
class TourBookingAdmin(admin.ModelAdmin):
    list_display = (
        "id", "customer", "tour", "partner", "booking_status_badge", "payment_status_badge", "trip_start_date", "created_at"
    )
    list_filter = ("status", "trip_start_date", "created_at", "country", "city", "partner")
    search_fields = ("customer__email", "tour__title", "payment_id")
    inlines = [BookingParticipantInline]

    readonly_fields = (
        "customer_info", "tour_info", "partner_info", "payment_id", "amount", "currency",
        "payment_status", "payment_method", "payment_made_at",
        "trip_start_date", "trip_end_date", "country", "city", "created_at", "updated_at", "status",
    )

    fieldsets = (
        ("Basic Info", {"fields": ("customer_info", "tour_info", "partner_info", "status")}),
        ("Payment Info", {"fields": ("payment_id", "amount", "currency", "payment_status", "payment_method", "payment_made_at")}),
        ("Trip Info", {"fields": ("trip_start_date", "trip_end_date", "country", "city")}),
        ("Order created", {"fields": ("created_at", "updated_at")}),
    )

    def customer_info(self, obj):
        customer = obj.customer
        return mark_safe(f"""
            <strong>Name:</strong> {customer.name} <br>
            <strong>Email:</strong> {customer.email} <br>
            <strong>Phone:</strong> {getattr(customer, 'phone', 'N/A')}
        """)
    customer_info.short_description = "Customer Info"

    def partner_info(self, obj):
        partner = obj.partner
        if not partner:
            return "No partner info"
        return mark_safe(f"""
            <strong>Name:</strong> {partner.first_name} - {partner.last_name} |
            <strong>Email:</strong> {partner.email} |
            <strong>Phone:</strong> {getattr(partner, 'phone', 'N/A')}
        """)
    partner_info.short_description = "Partner Info"

    def tour_info(self, obj):
        tour = obj.tour
        if not tour:
            return "No tour data"
        try:
            tour_url = reverse("admin:tours_tour_change", args=[tour.id])
        except:
            tour_url = "#"

        included_items = ", ".join([i.text for i in tour.included_items.all()]) or "-"
        excluded_items = ", ".join([e.text for e in tour.excluded_items.all()]) or "-"
        first_image = tour.images.first()
        image_html = f'<br><img src="{first_image.image.url}" width="200"/>' if first_image else ""
        languages = ", ".join(tour.language) if tour.language else "N/A"
        itinerary_preview = "".join(
            [f"<strong>Day {i.day_number}:</strong> {i.day_title or ''} - {i.description[:100]}...<br>"
             for i in tour.itineraries.all()[:3]]
        )

        return mark_safe(f"""
            <strong>Title:</strong> <a href="{tour_url}">{tour.title}</a><br>
            <strong>UUID:</strong> {tour.uuid}<br>
            <strong>Description:</strong> {tour.short_description or '-'}<br>
            <strong>City:</strong> {tour.city or '-'}<br>
            <strong>Country:</strong> {tour.country or '-'}<br>
            <strong>Languages:</strong> {languages}<br>
            <strong>Included:</strong> {included_items}<br>
            <strong>Excluded:</strong> {excluded_items}<br>
            {image_html}<br>
            <strong>Itinerary:</strong><br>{itinerary_preview}
        """)
    tour_info.short_description = "Tour Info"

    def payment_status(self, obj):
        latest = obj.payments.order_by('-created_at').first()
        return latest.status if latest else "N/A"
    payment_status.short_description = "Payment Status"

    def payment_status_badge(self, obj):
        status = self.payment_status(obj).upper()
        color = {
            "COMPLETED": "#28a745",  # Green
            "PENDING": "#ffc107",    # Orange
            "DENIED": "#dc3545",     # Red
            "REFUNDED": "#17a2b8",   # Blue
            "REVERSED": "#6f42c1"    # Purple
        }.get(status, "#6c757d")     # Default: gray

        return format_html(
            '<span style="padding:4px 8px; background-color:{}; color:white; border-radius:10px;">{}</span>',
            color,
            status.title()
        )
    payment_status_badge.short_description = "Payment Status"


    def booking_status_badge(self, obj):
        status = obj.status.upper()
        color = {
            "WAITING": "#ffc107",     # Yellow
            "COMPLETED": "#28a745",   # Green
            "FAILED": "#dc3545",      # Red
            "REFUNDED": "#17a2b8",    # Blue
        }.get(status, "#6c757d")      # Default: gray

        return format_html(
            '<span style="padding:4px 8px; background-color:{}; color:white; border-radius:10px;">{}</span>',
            color,
            status.title()
        )
    booking_status_badge.short_description = "Booking Status"

    def booking_status(self, obj):
        return obj.status
    booking_status.short_description = "Booking Status"

    def payment_method(self, obj):
        latest = obj.payments.order_by('-created_at').first()
        return latest.payment_method if latest else "N/A"
    payment_method.short_description = "Payment Method"

    def payment_made_at(self, obj):
        latest = obj.payments.order_by('-created_at').first()
        return latest.created_at.strftime("%Y-%m-%d %H:%M") if latest else "N/A"
    payment_made_at.short_description = "Payment Made At"

    def view_participants(self, obj):
        participants = obj.bookingparticipant_set.all()
        if not participants:
            return "No participants"
        return ", ".join([f"{p.first_name} {p.last_name}" for p in participants])
    view_participants.short_description = "Participants"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'partner_profile'):
            return qs.filter(partner=request.user.partner_profile)
        return qs.none()

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

# @admin.register(BookingParticipant)
# class BookingParticipantAdmin(admin.ModelAdmin):
#     list_display = ("first_name", "last_name", "id_type", "id_number", "date_of_birth", "booking")
#     list_filter = ("id_type",)
#     search_fields = ("first_name", "last_name", "id_number", "booking__id", "booking__customer__email")
#     raw_id_fields = ("booking",)
