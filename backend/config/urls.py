from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def home(request):
    return JsonResponse({"message": "API running"})

urlpatterns = [
    path("admin/", admin.site.urls),

    # ✅ correct for your structure
    path("api/v1/", include("apps.payouts.urls")),

    path("", home),
]