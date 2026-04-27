from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.payouts.models import BankAccount, LedgerEntry, Merchant, Payout
from apps.payouts.services import retry_stuck_payouts


class RetryTests(TestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(name="Retry Merchant")
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_holder_name="Retry Test",
            account_number="777788889999",
            ifsc_code="HDFC0001234",
        )

    def test_processing_payout_fails_after_max_attempts_and_releases_funds(self):
        payout = Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=5_000,
            status=Payout.Status.PROCESSING,
            attempts=2,
            next_retry_at=timezone.now() - timedelta(seconds=1),
        )
        Payout.objects.filter(id=payout.id).update(updated_at=timezone.now() - timedelta(seconds=45))
        payout.refresh_from_db()
        # Existing hold means money is reserved while processing.
        LedgerEntry.objects.create(
            merchant=self.merchant,
            payout=payout,
            entry_type=LedgerEntry.EntryType.HOLD,
            amount_paise=5_000,
        )

        # 0.85 maps to settlement failure in processing retry path.
        with patch("apps.payouts.services.random.random", return_value=0.85):
            retry_stuck_payouts()

        payout.refresh_from_db()
        self.assertEqual(payout.status, Payout.Status.FAILED)
        self.assertEqual(
            LedgerEntry.objects.filter(
                payout=payout,
                entry_type=LedgerEntry.EntryType.RELEASE,
                amount_paise=5_000,
            ).count(),
            1,
        )
