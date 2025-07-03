import requests
from rest_framework.response import Response
from django.conf import settings
import random
from django.utils.timezone import now, timedelta
from django.db.models import Count, Avg, Q

def custom_response(status_code=200, message="Success", data=None):
    return Response({
        "statuscode": status_code,
        "message": message,
        "data": data if data is not None else {}
    }, status=status_code)


def get_coordinates(location_name):
    api_key = settings.GOOGLE_MAPS_API_KEY
    endpoint = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {'address': location_name, 'key': api_key}
    response = requests.get(endpoint, params=params)

    if response.status_code == 200:
        results = response.json().get('results')
        if results:
            loc = results[0]['geometry']['location']
            return loc['lat'], loc['lng']
    return None, None



def generate_otp(length=4):
    return ''.join(str(random.randint(0, 9)) for _ in range(length))


def user_can_update_booking(user, booking):
    if user.is_superuser:
        return True
    if hasattr(user, 'partner_profile'):
        return booking.partner == user.partner_profile
    return False

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip



def calculate_trending_score():
    from tours.models import Tour ,TourAnalytics
    thirty_days_ago = now() - timedelta(days=30)

    tours = Tour.objects.all()

    for tour in tours:
        #view cas handled
        recent_views = TourAnalytics.objects.filter(
            tour=tour, event_type='view', timestamp__gte=thirty_days_ago
        ).count()

        #booking case handled
        recent_bookings = TourAnalytics.objects.filter(
            tour=tour, event_type='booking', timestamp__gte=thirty_days_ago
        ).count()

        #Average rating
         
        avg_rating = tour.rating_average or 0
        rating_count = tour.rating_count or 0
        recency_factor = 1.0 if (tour.last_booked_at and tour.last_booked_at >= thirty_days_ago) else 0.5

        # Weight calculation (example):
        score = (
            0.4 * recent_views +
            0.3 * recent_bookings +
            0.2 * avg_rating * rating_count +
            0.1 * recency_factor * 100  # scale recency
        )

        tour.trending_score = score
        tour.save(update_fields=['trending_score'])
