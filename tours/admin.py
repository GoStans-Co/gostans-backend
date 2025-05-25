from django.contrib import admin
from multiselectfield import MultiSelectField 
from django.utils.html import format_html
from .models import Tour, TourType, TourImage, IncludedItem, ExcludedItem, Itinerary ,TourTag
from django import forms
from partners.models import PartnerProfile
from django.core.exceptions import ValidationError


class TourImageInline(admin.TabularInline):
    model = TourImage
    extra = 1
    fields = ['image','image_preview']
    readonly_fields = ['image_preview']
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height: 100px; margin: 5px;" />', obj.image.url)
        return ""
    image_preview.short_description = 'Preview'

class IncludedItemInline(admin.TabularInline):
    model = IncludedItem
    extra = 1
    fields = ['text']
    verbose_name = "Included Item"
    verbose_name_plural = "Included Items"

class ExcludedItemInline(admin.TabularInline):
    model = ExcludedItem
    extra = 1
    fields = ['text']
    verbose_name = "Excluded Item"
    verbose_name_plural = "Excluded Items"

class ItineraryInline(admin.StackedInline):
    model = Itinerary
    extra = 1
    fields = ('day_number', 'day_title', 'description', 'accommodation', 'included_meals')
    show_change_link = True  # optional

@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    formfield_overrides = {
        MultiSelectField: {'widget': forms.SelectMultiple(attrs={'size': '4', 'style': 'width: 400px;'})},
    }
    list_display = ('title', 'tour_type', 'duration', 'price', 'city', 'country', 'group_size', 'display_languages','author_name','display_tags')
    inlines = [
        TourImageInline,
        IncludedItemInline,
        ExcludedItemInline,
        ItineraryInline,  # include itinerary inline here too
    ]
    fieldsets = (
        (None, {
            'fields': (
                'title', 'short_description','about', 'tour_type', 'duration', 'trip_start_date','trip_end_date',
                'price','currency', 'country', 'city', 'group_size',
                ('age_min', 'age_max'), 'language','tags','main_image','main_image_preview',
            )
        }),
    )
    readonly_fields = ['main_image_preview']
    def main_image_preview(self, obj):
        if obj.main_image:
            return format_html('<img src="{}" style="height: 150px; margin: 5px;" />', obj.main_image.url)
        return "(No image)"

    main_image_preview.short_description = 'Main Image Preview'

    def display_tags(self, obj):
        return ", ".join(tag.name for tag in obj.tags.all())
    display_tags.short_description = "Tags"

    def author_name(self, obj):
        if obj.partner and obj.partner.user:
            return obj.partner.user.get_full_name() or obj.partner.user.username
        return "N/A"
    author_name.short_description = "Author"
    

    def display_languages(self, obj):
        return ", ".join(obj.language)
    display_languages.short_description = "Languages"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            partner_profile = request.user.partner_profile  # note underscore here
        except PartnerProfile.DoesNotExist:
            return qs.none()
        return qs.filter(partner=partner_profile)

    def has_change_permission(self, request, obj=None):
        if obj is None:
            # Return True or False depending on whether the user can view the list at all.
            # Usually, partners can see their own tours, so allow.
            return True
        if not hasattr(request.user, 'partner_profile'):
            return False
        return obj.partner == request.user.partner_profile


    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True
        if request.user.is_superuser:
            return True
        try:
            return obj.partner == request.user.partner_profile
        except PartnerProfile.DoesNotExist:
            return False

    def save_model(self, request, obj, form, change):
        if not change:
            if request.user.is_superuser:
                # Assign the dummy PartnerProfile for superuser
                dummy_partner = PartnerProfile.objects.filter(user=request.user).first()
                if not dummy_partner:
                    raise ValidationError("Superuser does not have a dummy PartnerProfile. Please create one.")
                obj.partner = dummy_partner
            else:
                # Assign the logged-in partner's profile
                try:
                    obj.partner = request.user.partner_profile
                except PartnerProfile.DoesNotExist:
                    raise ValidationError("You do not have a partner profile to assign.")

        super().save_model(request, obj, form, change)

@admin.register(TourTag)
class TourTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    #filter_horizontal = ('tours',)
    search_fields = ('name', 'slug')

@admin.register(TourType)
class TourTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)