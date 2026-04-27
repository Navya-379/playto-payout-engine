import uuid

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LedgerEntry, Merchant, Payout
from .serializers import PayoutCreateSerializer
from .services import create_payout, get_balances


class PayoutCreateView(APIView):
    def post(self, request):
        serializer = PayoutCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = request.headers.get("Idempotency-Key")
        if not key:
            return Response({"detail": "Idempotency-Key header is required"}, status=400)
        try:
            idem_key = uuid.UUID(key)
        except ValueError:
            return Response({"detail": "Idempotency-Key must be UUID"}, status=400)

        body, code = create_payout(
            merchant_id=serializer.validated_data["merchant_id"],
            bank_account_id=serializer.validated_data["bank_account_id"],
            amount_paise=serializer.validated_data["amount_paise"],
            idem_key=idem_key,
        )
        return Response(body, status=code)


class MerchantDashboardView(APIView):
    def get(self, request, merchant_id: int):
        merchant = get_object_or_404(Merchant, id=merchant_id)
        ledger = list(
            LedgerEntry.objects.filter(merchant=merchant)
            .order_by("-created_at")
            .values("id", "entry_type", "amount_paise", "created_at")[:20]
        )
        payouts = list(
            Payout.objects.filter(merchant=merchant)
            .order_by("-created_at")
            .values("id", "status", "amount_paise", "attempts", "created_at", "updated_at")[:20]
        )
        return Response(
            {
                "merchant_id": merchant.id,
                "balances": get_balances(merchant.id),
                "recent_ledger_entries": ledger,
                "payouts": payouts,
            }
        )
