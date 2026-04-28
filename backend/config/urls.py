from django.urls import include, path
from django.http import JsonResponse

def home(request):
    return JsonResponse({
        "message": "Playto Payout Engine API is running"
    })

urlpatterns = [
    path("", home),
    path("api/v1/", include("apps.payouts.urls")),
]
