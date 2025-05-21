from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from customer_auth.models import CustomerUser
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist


class CustomerUserJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_id = validated_token.get(settings.SIMPLE_JWT.get("USER_ID_CLAIM", "user_id"))
            return CustomerUser.objects.get(id=user_id)
        except (CustomerUser.DoesNotExist, ObjectDoesNotExist):
            raise InvalidToken("User not found")
