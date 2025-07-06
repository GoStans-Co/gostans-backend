from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from django.urls import path, re_path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

# 📘 Custom Swagger Description
API_DESCRIPTION = """
## 📘 GoStans API Overview


Welcome to the GoStans API documentation. This documentation provides details on all API endpoints categorized by usage.

### ✅ Public APIs
No authentication required.

### 👤 User APIs
Require login via JWT Bearer token. Includes login, signup, profile, cart.

### 🧳 Tour APIs
Tour listings, filters, booking, and analytics.

### 💳 Payment APIs
Razorpay and PayPal integrations with webhooks.

---

### 🔐 Authentication Header

All private APIs require this HTTP header:


---

### ⚠️ Status Codes

| Code | Description             |
|------|--------------------------|
| ✅ 200 | OK (Success)           |
| 🔴 400 | Bad request            |
| 🔐 401 | Unauthorized           |
| 🚫 403 | Forbidden              |
| 🔍 404 | Not found              |
| 💥 500 | Internal server error |

> 🔒 In production, all 400/500 messages should be **generalized**
"""

schema_view = get_schema_view(
    openapi.Info(
        title="GoStans API",
        default_version='v1',
        description=API_DESCRIPTION,
        contact=openapi.Contact(email="support@gostans.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

def health_check(request):
    return JsonResponse({"status": "ok", "message": "Project is running!"})

urlpatterns = [
    path('health/', health_check),
    path('admin/', admin.site.urls),

    path('api/v1/auth/', include('customer_auth.urls.auth_urls')),   #  auth endpoints
    path('api/v1/user/', include('customer_auth.urls.users_urls')),  # profile endpoints
    path('api/v1/user/', include('partners.urls')),              
    path('api/v1/tours/', include('tours.urls')), 
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
