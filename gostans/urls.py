from django.http import JsonResponse
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.views.i18n import set_language

def health_check(request):
    return JsonResponse({"status": "ok", "message": "Project is running!"})

urlpatterns = [
    path('health/', health_check),
    path('admin/', admin.site.urls),
    path('api/auth/', include('customer_auth.urls')),  # API for normal users
    path('api/auth/', include('customer_auth.urls')),  # API for normal users
    path('set_language/', set_language, name='set_language'),
    path('api/location/', include('location.urls')),
    path('chaining/', include('smart_selects.urls')),

    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
