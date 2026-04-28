from django.urls import path
from .views import MerchantDashboardView, PayoutCreateView
from django.http import JsonResponse

def api_home(request):
    return JsonResponse({"message": "API v1 working"})

urlpatterns = [
    path("", api_home),
    path("payouts/", PayoutCreateView.as_view()),
    path("merchants/<int:merchant_id>/dashboard/", MerchantDashboardView.as_view()),
]
