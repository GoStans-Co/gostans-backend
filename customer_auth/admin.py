from django.contrib import admin
from django.utils.translation import get_language
from django.utils.html import format_html
from django import forms
from .models import CustomerUser

class CustomerUserAdminForm(forms.ModelForm):
    class Meta:
        model = CustomerUser
        fields = '__all__'


@admin.register(CustomerUser)
class CustomerUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'phone', 'is_active', 'date_joined','image_preview','get_oauth_provider')
    search_fields = ('email', 'name', 'phone')
    list_filter = ('is_active',)
    readonly_fields = ('image_preview',) 
    exclude = ['password']

    def get_oauth_provider(self, obj):
        return obj.oauth_provider or "DEFAULT"
        
    get_oauth_provider.short_description = 'Registered From'  

    def image_preview(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;" />', obj.image.url)
        return "(No image)"

    image_preview.short_description = 'Image Preview'

    def get_form(self, request, obj=None, **kwargs):
        lang = get_language()
        form = super().get_form(request, obj, **kwargs)

        # Dynamically filter translated fields for current language
        new_fields = {}
        for field_name in list(form.base_fields):
            if field_name.endswith(f"_{lang}"):
                base_name = field_name.rsplit("_", 1)[0]
                field = form.base_fields.pop(field_name)
                field.label = base_name.capitalize()
                new_fields[base_name] = field

        # Replace form fields with translated ones
        form.base_fields = new_fields | form.base_fields  # Python 3.9+

        return form

    def get_fields(self, request, obj=None):
        # Customize form layout
        return ['email', 'name', 'phone','image_preview','is_active','date_joined',]


    def get_readonly_fields(self, request, obj=None):
        return ['date_joined','image_preview']

    def has_add_permission(self, request):
        """Prevents adding new users from the admin panel."""
        return False  # Disables the "Add" button

