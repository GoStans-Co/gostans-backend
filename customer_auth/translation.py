# translation.py

from modeltranslation.translator import register, TranslationOptions
from .models import CustomerUser


@register(CustomerUser)
class CustomerUserTranslationOptions(TranslationOptions):
    fields = ('email', 'name', 'phone',)
