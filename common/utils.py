import requests
from rest_framework.response import Response
from django.conf import settings

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