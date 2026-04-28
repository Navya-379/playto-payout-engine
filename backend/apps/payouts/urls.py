from django.urls import path
from django.http import JsonResponse
from .views import MerchantDashboardView, PayoutCreateView

def api_home(request):
    return JsonResponse({"message": "API v1 working"})

urlpatterns = [
    path("", api_home, name="api-home"),
    path("payouts/", PayoutCreateView.as_view(), name="payout-create"),
    path("merchants/<int:merchant_id>/dashboard/", MerchantDashboardView.as_view(), name="merchant-dashboard"),
]
