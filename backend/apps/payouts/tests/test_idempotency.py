import uuid

from django.test import TestCase
from rest_framework.test import APIClient

from apps.payouts.models import BankAccount, LedgerEntry, Merchant, Payout


class IdempotencyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.merchant = Merchant.objects.create(name="Idempotency Merchant")
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_holder_name="Test",
            account_number="1234567890",
            ifsc_code="HDFC0001234",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=10_000,
        )

    def test_same_key_returns_same_response(self):
        payload = {
            "merchant_id": self.merchant.id,
            "bank_account_id": self.bank_account.id,
            "amount_paise": 6000,
        }
        idem_key = str(uuid.uuid4())
        first = self.client.post("/api/v1/payouts", payload, format="json", HTTP_IDEMPOTENCY_KEY=idem_key)
        second = self.client.post("/api/v1/payouts", payload, format="json", HTTP_IDEMPOTENCY_KEY=idem_key)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(Payout.objects.count(), 1)
