from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

admin.site.site_header = "Gostance Admin Panel"
admin.site.site_title = "Gostance Dashboard"
admin.site.index_title = "Welcome to Gostance CMS"

# Unregister the default ones
admin.site.unregister(User)
admin.site.unregister(Group)

if OutstandingToken in admin.site._registry:
    admin.site.unregister(OutstandingToken)

if BlacklistedToken in admin.site._registry:
    admin.site.unregister(BlacklistedToken) 

# Customize display names
User._meta.verbose_name = 'Package Provider'
User._meta.verbose_name_plural = 'Package Providers'

Group._meta.verbose_name = 'Package Group'
Group._meta.verbose_name_plural = 'Package Groups'


# Re-register with custom labels
admin.site.register(User, UserAdmin)
admin.site.register(Group, GroupAdmin)

