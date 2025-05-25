from django.contrib import admin
from .models import Country, City

class CityInline(admin.TabularInline):
    model = City
    extra = 1 

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name']
    inlines = [CityInline]

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'country']
    list_filter = ['country']
