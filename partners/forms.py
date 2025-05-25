from django import forms
from .models import PartnerProfile, Country, City

class PartnerProfileForm(forms.ModelForm):
    class Meta:
        model = PartnerProfile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter city queryset based on selected country (instance or POST data)
        if self.instance and self.instance.pk:
            country = self.instance.country
        else:
            country = self.data.get('country') or None

        if country:
            try:
                country_obj = Country.objects.get(pk=country)
                self.fields['city'].queryset = City.objects.filter(country=country_obj).order_by('name')
            except Country.DoesNotExist:
                self.fields['city'].queryset = City.objects.none()
        else:
            self.fields['city'].queryset = City.objects.none()
