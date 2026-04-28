from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

# Root API health check (safe)
def home(request):
    return JsonResponse({
        "message": "Playto Payout Engine API is running"
    })

urlpatterns = [
    # ✅ Admin must always be first and exact
    path("admin/", admin.site.urls),

    # ✅ API routes
    path("api/v1/", include("apps.payouts.urls")),

    # ✅ Root endpoint (optional health check)
    path("", home),
]
