import uuid
from concurrent.futures import ThreadPoolExecutor

from django.test import TransactionTestCase
from rest_framework.test import APIClient

from apps.payouts.models import BankAccount, LedgerEntry, Merchant, Payout


class ConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(name="Concurrency Merchant")
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_holder_name="Test",
            account_number="9988776655",
            ifsc_code="HDFC0001234",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=10_000,
        )

    def _post(self, key: str) -> int:
        client = APIClient()
        response = client.post(
            "/api/v1/payouts",
            {
                "merchant_id": self.merchant.id,
                "bank_account_id": self.bank_account.id,
                "amount_paise": 6000,
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        return response.status_code

    def test_parallel_requests_allow_only_one_success(self):
        keys = [str(uuid.uuid4()), str(uuid.uuid4())]
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(self._post, keys))

        self.assertEqual(results.count(201), 1)
        self.assertEqual(results.count(400), 1)
        self.assertEqual(Payout.objects.count(), 1)
