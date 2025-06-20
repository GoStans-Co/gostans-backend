from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import TourBooking, BookingParticipant

class BookingParticipantInline(admin.TabularInline):
    model = BookingParticipant
    extra = 0
    readonly_fields = ("first_name", "last_name", "id_type", "id_number", "date_of_birth")


@admin.register(TourBooking)
class TourBookingAdmin(admin.ModelAdmin):
    list_display = (
        "id", "customer", "tour", "partner", "status", "trip_start_date", "created_at", "view_participants"
    )
    list_filter = ("status", "trip_start_date", "created_at", "country", "city", "partner")
    search_fields = ("customer__email", "tour__title", "payment_id")
    list_editable = ("status",)
    inlines = [BookingParticipantInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'partner_profile'):
            return qs.filter(partner=request.user.partner_profile)
        return qs.none()

    def view_tour_info(self, obj):
        return f"{obj.tour.title} ({obj.tour.id})"
    view_tour_info.short_description = "Tour"

    
    def view_customer_info(self, obj):
        return f"{obj.customer.name} ({obj.customer.email})"
    view_customer_info.short_description = "Customer"

    def view_partner_info(self, obj):
        return f"{obj.partner.user.username} ({obj.partner.phone})"
    view_partner_info.short_description = "Partner"

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj and hasattr(request.user, 'partner_profile'):
            return obj.partner == request.user.partner_profile
        return False

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def view_participants(self, obj):
        url = (
            reverse('admin:order_bookingparticipant_changelist')  # Replace YOUR_APP_LABEL here
            + f'?booking__id__exact={obj.id}'
        )
        return format_html(f'<a href="{url}">View Participants</a>')


@admin.register(BookingParticipant)
class BookingParticipantAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "id_type", "id_number", "date_of_birth", "booking")
    list_filter = ("id_type",)
    search_fields = ("first_name", "last_name", "id_number", "booking__id", "booking__customer__email")
    raw_id_fields = ("booking",)
