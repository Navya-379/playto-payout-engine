from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def home(request):
    return JsonResponse({
        "message": "Playto Payout Engine API is running"
    })

urlpatterns = [
    path("admin/", admin.site.urls),

    # IMPORTANT: correct app include
    path("api/v1/", include("payouts.urls")),

    path("", home),
]
