import nested_admin
from django.contrib import admin
from multiselectfield import MultiSelectField 
from django import forms
from django.utils.html import format_html
from .models import Tour, TourType, TourImage, IncludedItem, ExcludedItem, ItineraryDay, ItinerarySlot,TourTag,TourPricing,TourAnalytics,Destination
from partners.models import PartnerProfile
from django.core.exceptions import ValidationError
from django.contrib import messages
from multiupload.fields import MultiFileField
from django.shortcuts import redirect
from django.forms import TimeInput,Textarea
from django.utils.html import format_html

# class TourForm(forms.ModelForm):
#     included_items_text = forms.CharField(
#         required=False,
#         widget=forms.TextInput(attrs={
#             'style': 'width: 400px;',
#             'placeholder': 'Add multiple items separated by commas',
#             'data-role': 'tagsinput',  # JS library for tag-style input
#         })
#     )

#     class Meta:
#         model = Tour
#         fields = '__all__'

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Smaller textareas
#         self.fields['short_description'].widget.attrs.update({'rows': 2, 'cols': 50})
#         self.fields['about'].widget.attrs.update({'rows': 5, 'cols': 80})

#         if self.instance.pk:
#             self.fields['included_items_text'].initial = ", ".join(
#                 item.text for item in self.instance.included_items.all()
#             )

#     def save(self, commit=True):
#         tour = super().save(commit)
#         text_values = self.cleaned_data.get('included_items_text', '').split(',')
#         tour.included_items.all().delete()
#         for t in text_values:
#             t = t.strip()
#             if t:
#                 IncludedItem.objects.create(tour=tour, text=t)
#         return tour


class ItinerarySlotForm(forms.ModelForm):
    class Meta:
        model = ItinerarySlot
        fields = '__all__'
        widgets = {
            'start_time': TimeInput(attrs={'type': 'time'}),
            'end_time': TimeInput(attrs={'type': 'time'}),
            'description': Textarea(attrs={
                'rows': 3,   # reduces height
                'cols': 40,  # optional, width control
                'style': 'resize: vertical;'  # allow vertical resize only
            }),
        }

class ItineraryDayForm(forms.ModelForm):
    class Meta:
        model = ItineraryDay
        fields = '__all__'
        widgets = {
            'description': Textarea(attrs={
                'rows': 3,        # smaller height
                'cols': 40,       # smaller width
                'style': 'resize: vertical;'  # allow vertical resizing only
            }),
        }

class TourImageUploadForm(forms.Form):
    images = MultiFileField(
        min_num=1,
        max_num=20,
        max_file_size=1024*1024*5,
        required=False,
        label="Upload Multiple Images"
    )


class TourImageInline(nested_admin.NestedTabularInline):
    model = TourImage
    extra = 1
    fields = ['image','image_preview']
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height: 100px; margin: 5px;" />', obj.image.url)
        return ""
    image_preview.short_description = 'Preview'

# class includedItemInlineForm(forms.ModelForm):
#     # text = forms.CharField(
#     #     widget=forms.TextInput(attrs={
#     #         'style': 'width: 400px;',
#     #         'placeholder': 'Add multiple items separated by commas',
#     #         'data-role': 'tagsinput',  # for JS tag library
#     #     }),
#     #     required=False
#     # )
#     included_text = forms.CharField(   # ← you need this instead of redefining `text`
#         widget=forms.TextInput(attrs={
#             'style': 'width: 400px;',
#             'placeholder': 'Add multiple items separated by commas',
#             'data-role': 'tagsinput',
#         }),
#         required=False
#     )

#     class Meta:
#         model = IncludedItem
#         fields = '__all__'

#     # def __init__(self, *args, **kwargs):
#     #     super().__init__(*args, **kwargs)
#     #     if self.instance.pk:
#     #         # Prepopulate the field with existing included items
#     #         self.fields['included_text'].initial = ", ".join(
#     #             item.text for item in self.instance.included_items.all()
#     #         )

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # IMPORTANT: only try to use included_items if this is a Tour
#         if self.instance and hasattr(self.instance, "tour") and self.instance.tour_id:
#             self.fields['included_text'].initial = ", ".join(
#                 item.text for item in self.instance.tour.included_items.all()
#             )

#     def save(self, commit=True):
#         included_item = super().save(commit=False)
#         tour = included_item.tour

#         if commit:
#             included_item.save()

#             if 'included_text' in self.cleaned_data:
#                 text_values = self.cleaned_data['included_text'].split(',')
#                 # Clear old items
#                 tour.included_items.all().delete()
#                 # Create new ones
#                 for t in text_values:
#                     t = t.strip()
#                     if t:
#                         IncludedItem.objects.create(tour=tour, text=t)
#         return included_item


# class IncludedItemInline(nested_admin.NestedTabularInline):
#     model = IncludedItem
#     extra = 1
#     fields = ['text']
#     can_delete = False 
#     verbose_name = "Included Item"
#     verbose_name_plural = "Included Items"
#     form = includedItemInlineForm

#     class Media:
#         css = {
#             'all': ('css/hide_inline_add.css',) 
#         }


class includedItemInlineForm(forms.ModelForm):
    text = forms.CharField(
        widget=forms.TextInput(attrs={
            'style': 'width: 400px;',
            'placeholder': 'Add items (comma-separated allowed)',
            'data-role': 'tagsinput',
        }),
        required=False
    )

    class Meta:
        model = IncludedItem
        fields = ['text']

    def clean_text(self):
        text = self.cleaned_data['text']
        # store only the raw text in this row
        return text

class IncludedItemInline(nested_admin.NestedTabularInline):
    model = IncludedItem
    form = includedItemInlineForm
    extra = 0
    fields = ['text']
    can_delete = False
    verbose_name = "Included Item"
    verbose_name_plural = "Included Items"




class ExcludedItemInlineForm(forms.ModelForm):
    text = forms.CharField(
        widget=forms.TextInput(attrs={
            'style': 'width: 400px;',
            'placeholder': 'Add multiple items separated by commas',
            'data-role': 'tagsinput',  # for JS tag library
        }),
        required=False
    )

    class Meta:
        model = ExcludedItem
        fields = '__all__'

    def clean_text(self):
        # Convert comma-separated input into list if needed
        text = self.cleaned_data['text']
        items = [t.strip() for t in text.split(',') if t.strip()]
        return ', '.join(items)


class ExcludedItemInline(nested_admin.NestedTabularInline):
    model = ExcludedItem
    extra = 0
    fields = ['text']
    can_delete = False 
    verbose_name = "Excluded Item"
    verbose_name_plural = "Excluded Items"
    form = ExcludedItemInlineForm

class ItinerarySlotInline(nested_admin.NestedStackedInline):
    model = ItinerarySlot
    extra = 0
    form = ItinerarySlotForm 
    fields = (('start_time', 'end_time'), 'title', 'description','included_meals','location_name')
    readonly_fields = ('latitude', 'longitude')
    ordering = ('start_time',)

class ItineraryDayInline(nested_admin.NestedStackedInline):
    model = ItineraryDay
    form = ItineraryDayForm 
    extra = 0
    fields = ('day_number', 'day_title', 'description','accommodation','included_meals')
    inlines = [ItinerarySlotInline]  # nested slots inside day



class TourPricingInline(nested_admin.NestedTabularInline):
    model = TourPricing
    extra = 1



@admin.register(Tour)
class TourAdmin(nested_admin.NestedModelAdmin):
    search_fields = ['title','city__name','country__name','partner__user__username']
    
    # Make textareas smaller for certain fields
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'short_description':
            kwargs['widget'] = forms.Textarea(attrs={'rows': 2, 'cols': 50})
        elif db_field.name == 'about':
            kwargs['widget'] = forms.Textarea(attrs={'rows': 5, 'cols': 80})
        return super().formfield_for_dbfield(db_field, **kwargs)

    formfield_overrides = {
        MultiSelectField: {'widget': forms.SelectMultiple(attrs={'size': '4', 'style': 'width: 400px;'})},
    }
    

    # Use duration_display instead of raw duration
    list_display = ('id','title','is_active', 'tour_type', 'get_duration_display', 'price', 'city', 'country', 'group_size', 'display_languages','display_tags','author_name','created_at')
    list_editable = ('is_active',) 
    save_on_top = True
    
    inlines = [
        TourPricingInline,
        TourImageInline,
        IncludedItemInline,
        ExcludedItemInline,
        ItineraryDayInline,  # include itinerary inline here too
    ]

    fieldsets = (
        (None, {
            'fields': (
                'title', 'short_description','about', 'tour_type', 'duration_days','duration_hours', ('trip_start_date','trip_end_date'),
                ('price','currency'), ('country', 'city'), 'group_size',
                ('age_min', 'age_max'), 'language','tags','main_image','main_image_preview',
            )
        }),
    )
    readonly_fields = ['main_image_preview','created_at']


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

    def get_duration_display(self, obj):
        return obj.duration_display
    get_duration_display.admin_order_field = 'duration_days'
    get_duration_display.short_description = 'Duration'


    def display_languages(self, obj):
        return ", ".join(obj.language)
    display_languages.short_description = "Languages"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            partner_profile = request.user.partner_profile
        except PartnerProfile.DoesNotExist:
            return qs.none()
        return qs.filter(partner=partner_profile)

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        if not hasattr(request.user, 'partner_profile'):
            return False
        return obj.partner == request.user.partner_profile

    def has_delete_permission(self, request, obj=None):
        if obj is None or request.user.is_superuser:
            return True
        try:
            return obj.partner == request.user.partner_profile
        except PartnerProfile.DoesNotExist:
            return False

    def changelist_view(self, request, extra_context=None):
        messages.info(request, "🔍 You can search by: Tour Title, City Name, Country Name and Author Name.")
        return super().changelist_view(request, extra_context)
    
    def save_model(self, request, obj, form, change):
        if not change:
            if request.user.is_superuser:
                dummy_partner = PartnerProfile.objects.filter(user=request.user).first()
                if not dummy_partner:
                    raise ValidationError("Superuser does not have a dummy PartnerProfile. Please create one.")
                obj.partner = dummy_partner
            else:
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


@admin.register(TourAnalytics)
class TourAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['id', 'tour', 'event_type', 'user', 'timestamp']
    list_filter = ['event_type', 'timestamp']
    search_fields = ['tour__title', 'user__email', 'session_id', 'ip_address']
    readonly_fields = ['timestamp']

@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'country')
    search_fields = ('name', 'city__name', 'country__name')
    list_filter = ('country',)