# partners/admin.py

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm

from .models import PartnerProfile
from .forms import PartnerProfileForm



class PartnerProfileInline(admin.StackedInline):
    model = PartnerProfile
    can_delete = False
    verbose_name_plural = 'Partner Profile'

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    # Custom User admin that includes the inline
class UserAdmins(BaseUserAdmin):
    inlines = (PartnerProfileInline,)
    list_display = ('username', 'email', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active')

class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'email', 'password1', 'password2'),
        }),
    )

    inlines = (PartnerProfileInline,)

    # Optionally you can customize list_display, list_filter, etc
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active')

# Unregister default User admin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)