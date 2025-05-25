from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import GroupAdmin
from partners.admin import UserAdmin 

admin.site.site_header = "Gostance Admin Panel"
admin.site.site_title = "Gostance Dashboard"
admin.site.index_title = "Welcome to Gostance CMS"

# Unregister the default ones
admin.site.unregister(User)
admin.site.unregister(Group)

# Customize display names
User._meta.verbose_name = 'Partner'
User._meta.verbose_name_plural = 'Add Partner'

Group._meta.verbose_name = 'Group'
Group._meta.verbose_name_plural = 'Add Group'


# Re-register with custom labels
admin.site.register(User, UserAdmin)
admin.site.register(Group, GroupAdmin)

